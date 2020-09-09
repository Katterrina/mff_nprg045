#!/usr/bin/env python3
import sys

from pyNN.random import RandomDistribution
from mozaik.tools.distribution_parametrization import MozaikExtendedParameterSet, load_parameters, PyNNDistribution
from mozaik.storage.datastore import Hdf5DataStore,PickledDataStore
from mozaik.analysis.data_structures import Connections
from mozaik.storage import queries

from parameters import UniformDist
from json import JSONEncoder
from parameters import ParameterSet

from numpy import arange
from bokeh.plotting import figure, curdoc, from_networkx, show
from bokeh.models import (BoxZoomTool, Circle, HoverTool, Range1d,
						  MultiLine, Plot, Range1d, ResetTool,GraphRenderer)
import networkx as nx
from functools import partial


def get_datastore(path_to_datastore):
	datastore = PickledDataStore(
					load=True,
					parameters=ParameterSet(
						{'root_directory': path_to_datastore ,'store_stimuli' : False}),
					replace=False)
	return datastore

def get_neuron_positions_on_sheet(datastore, sheet):
	positions = {
		'x' : datastore.get_neuron_positions()[sheet][0],
		'y' : datastore.get_neuron_positions()[sheet][1]
	}
		
	return positions

def add_connection_edges(G, source, target, conn_weights, conn_delays):
	connection_edges = [(i+source,j+target,{'weight':w, 'delay':d})
						for ((i,j,w),(_,_,d))
						in zip(conn_weights,conn_delays)]

	G.add_edges_from(connection_edges)

def add_sheet_nodes_to_graph(G,datastore,n,sheet):
	positions = get_neuron_positions_on_sheet(datastore,sheet)
	
	number_of_nodes = len(positions['x'])
	node_indices = [i for i in range(number_of_nodes)]
	nodes_with_sheet = [(i+n,{"coor":(positions['x'][i],positions['y'][i])})
						for i
						in node_indices]
		
	G.add_nodes_from(nodes_with_sheet,sheet=sheet)

	return n + number_of_nodes

def create_neuron_connections_graph(datastore):
	G = nx.DiGraph()

	sheet_nodes_start_number = {}
	n = 0

	for sheet in datastore.sheets():
		sheet_nodes_start_number[sheet] = n
		n = add_sheet_nodes_to_graph(G,datastore,n,sheet)

	connections = datastore.get_analysis_result(identifier='Connections')

	for conn in connections:
		c_weights = conn.weights
		c_delays = conn.delays
		add_connection_edges(G,
							sheet_nodes_start_number[conn.source_name],
							sheet_nodes_start_number[conn.target_name],
							c_weights, c_delays)

	return G

def get_sheet_subgraphs(G,sheets):
	subgraphs = {}
	
	for sheet in sheets:
		sheet_nodes = [n for n,attr in G.nodes(data=True) if attr["sheet"]==sheet]
		subgraphs[sheet] = G.subgraph(sheet_nodes)
  
	return subgraphs

def create_sheet_graph_renderer(G,sheet):
	sheet_nodes = [(n,attr) for n,attr in G.nodes(data=True) if attr["sheet"]==sheet]
	sheet_subgraph = nx.DiGraph()
	sheet_subgraph.add_nodes_from(sheet_nodes)
	layout = get_nodes_layout(sheet_subgraph)
	graph_renderer = from_networkx(sheet_subgraph,layout)

	graph_renderer.node_renderer.data_source.add([0] * len(sheet_nodes), 'selected_neighbors')

	return graph_renderer

def get_nodes_layout(G):
	layout = {n:G.nodes[n]["coor"] for n in G.nodes()}
	return layout

	
def update_renderers_after_selection(event,nx_graph,this_sheet,sheets,edges_in_rbgroup):
	edges_in = edges_in_rbgroup.active

	if event.final:
		update_nodes_and_edges_data(nx_graph,this_sheet,sheets,edges_in)


def selected_nx_index(graph_renderer,new_data_nodes):
	selected_indicies = []

	source = graph_renderer.node_renderer.data_source
	indicies_in_renderer = source.selected.indices

	for i in indicies_in_renderer:	
		node_index = source.data["index"][i]
		selected_indicies.append(node_index)
		new_data_nodes[i] = 1

	return selected_indicies

def update_nodes_and_edges_data(nx_graph,this_sheet,sheets,edges_in):
	graph_renderer = curdoc().select({"name":this_sheet})[0]

	nodes_data_source = graph_renderer.node_renderer.data_source
	edges_data_source = graph_renderer.edge_renderer.data_source

	new_data_nodes = [0] * len(nodes_data_source.data["selected_neighbors"])

	selected_nx_indicies = selected_nx_index(graph_renderer,new_data_nodes)

	edges = {'start':[], 'end':[], 'weight':[],'delay':[]}
 
	neighbors_in_other_sheets = { s:[] for s in sheets }

	for node in selected_nx_indicies:

		neighbors = get_neighbors(node,nx_graph, edges_in)

		for ng in neighbors:

			if nx_graph.nodes[ng]["sheet"] == this_sheet:
				p = nodes_data_source.data["index"].index(ng)
				if new_data_nodes[p] == 0:
					new_data_nodes[p] = 2

				if edges_in:
					append_edge_to_edges_dict(edges,nx_graph,ng,node)
				else:
					append_edge_to_edges_dict(edges,nx_graph,node,ng)
			else:
				neighbors_in_other_sheets[nx_graph.nodes[ng]["sheet"]].append(ng)

	nodes_data_source.data["selected_neighbors"] = new_data_nodes
	edges_data_source.data = edges

	update_neighbors_in_other_sheets(neighbors_in_other_sheets,this_sheet)

def update_neighbors_in_other_sheets(neighbors_dict,active_sheet):

	for graph_renderer in curdoc().select({"type":GraphRenderer}):

		if graph_renderer.name == active_sheet:
			continue

		nodes_data_source = graph_renderer.node_renderer.data_source
		new_data_nodes = [0] * len(nodes_data_source.data["selected_neighbors"])

		for node in neighbors_dict[graph_renderer.name]:
			p = nodes_data_source.data["index"].index(node)
			new_data_nodes[p] = 2 

		nodes_data_source.data["selected_neighbors"] = new_data_nodes

		edges_data_source = graph_renderer.edge_renderer.data_source
		edges_data_source.data = {'start':[], 'end':[], 'weight':[],'delay':[]}

def append_edge_to_edges_dict(edges_dict, nx_graph, start, end):
	edges_dict['start'].append(start)
	edges_dict['end'].append(end)
	edges_dict['weight'].append(nx_graph.edges[(start,end)]["weight"])
	edges_dict['delay'].append(nx_graph.edges[(start,end)]["delay"])
 
def get_neighbors(node,nx_graph, edges_in):
	neighbors = []
	if edges_in:
		neighbors = nx_graph.predecessors(node)
	else:
		neighbors = nx_graph.successors(node)

	return neighbors
    

def get_ranges(coors_list):
	min_x = 0
	max_x = 0
	min_y = 0
	max_y = 0
	for coor in coors_list:
		x = coor[0]
		y = coor[1]
		if x<min_x:
			min_x = x
		if x>max_x:
			max_x=x
		if y<min_y:
			min_y=y
		if y>max_y:
			max_y=y

	return (Range1d(min_x,max_x),Range1d(min_y,max_y))

def reset_visualization(source):
    	raise NotImplementedError

#--------------------------------------------------------------------

def change_selection(positions,nodes_data_source,value_to_selected):
	selected_indicies = []
	nodes_data = nodes_data_source.data

	patch_data = []

	for p in positions:
		node_index = nodes_data["index"][p]
		selected_indicies.append(node_index)
		patch_data.append((p,value_to_selected))

	print(patch_data)
	nodes_data_source.patch({'selected_neighbors': patch_data})

	return selected_indicies

def update_renderers_according_selection2(attr, old, new, nx_graph, this_renderer, edges_in=False):
	old_set = set(old)
	new_set = set(new)

	added_set = new_set.difference(old_set)
	removed_set = old_set.difference(new_set)

	# indicies removed from selection
	removed = change_selection(removed_set,this_renderer.node_renderer.data_source,0)
	added = change_selection(added_set,this_renderer.node_renderer.data_source,1)
 
 
