import yaml
import random
import numpy as np
import math
import os

"""
obstacle list -> [(x,y,r), (x1,y1,r1), (x2,y2,r2)], gdzie:
    x,y to współrzędne przeszkody
    r to promień przeszkody powiększony o promień łazika
"""

class Node:
    def __init__(self, x, y):
        self.x_ = x
        self.y_ = y
        self.parent_ = None
        self.cost_= 0

class RRTStar:
    def __init__(self, sim,  start, goal, obstacle_list):
        self.sim_ = sim
        # common params for rrt*, constant in simulation, need to be fit for enviroment
        config_path = os.path.join(os.path.dirname(__file__), "rrt_star_config.yaml")
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.map_size_ub_ = config['map_size_ub']
        self.map_size_lb_ = config['map_size_lb']
        self.step_size_ = config['step_size']
        self.max_ierations_ = config['max_ierations']
        self.generate_chance_ = config['generate_chance']
        self.search_radius_ = config['search_radius']
        self.goal_radius_ = config['goal_radius']
        # individual params for each rover
        self.start_ = Node(start[0], start[1])
        self.goal_ = Node(goal[0], goal[1])
        self.obstacles_ = obstacle_list
        self.node_list_ = [self.start_]
        self.path_ = None
        self.goal_reached_ = False

    # generate random node in space (with chance to generate target)
    def generate_node(self):
        if random.randint(0, 1) > self.generate_chance_:
            new_node = Node(random.uniform(self.map_size_lb_[0], self.map_size_ub_[0]), random.uniform(self.map_size_lb_[1], self.map_size_ub_[1]))
        else:
            new_node = self.goal_
        return new_node

    # find in tree node nearest to given one
    def get_nearest_node(self, target_node):
        distances = []
        for candidate in self.node_list_:
            distances.append(np.linalg.norm([target_node.x_ - candidate.x_, target_node.y_ - candidate.y_]))
        nearest_node = self.node_list_[np.argmin(distances)]
        return nearest_node
    
    # generate node in direction to target node
    def steer(self, from_node, target_node):
        # calculate direction
        theta = math.atan2(target_node.y_ - from_node.y_, target_node.x_ - from_node.x_)
        # move for step_size in direction and update cost 
        new_node = Node(from_node.x_ + self.step_size_ * math.cos(theta), from_node.y_ + self.step_size_ * math.sin(theta))
        new_node.cost_ = from_node.cost_ + self.step_size_
        new_node.parent_ = from_node
        return new_node

    # check for collision with obstalces
    def check_collision(self, node):
        for obstacle in self.obstacles_:
            distance = np.linalg.norm([node.x_ - obstacle[0], node.y_ - obstacle[1]])
            if distance <= obstacle[2]:
                return True
        return False

    # find nodes nearby given node (in search_radius) 
    def find_neighbors(self, node):
        neighbors = []
        for candidate in self.node_list_:
            distance = np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if distance <= self.search_radius_:
                neighbors.append(candidate)
        return neighbors 

    # choose parent for new node (from nearest and neighbours)
    def choose_parent(self, neighbors, closest_node, node):
        # define node to which given node will be connected to
        min_cost = closest_node.cost_ + np.linalg.norm([node.x_ - closest_node.x_, node.y_ - closest_node.y_])
        best_node = closest_node
        # check if there isnt better option in neighbouring nodes
        for candidate in neighbors:
            cand_cost = candidate.cost_ + np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if (cand_cost < min_cost) and not self.check_collision(candidate):
                min_cost = cand_cost
                best_node = candidate
        node.cost_ = min_cost
        node.parent_ = best_node
        return node

     # check for better connections between nodes (setting new node as parent of nodes in radius)
    def rewire(self, neighbors, node):
         for candidate in neighbors:
            cand_cost = node.cost_ + np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if (cand_cost < candidate.cost_) and not self.check_collision(candidate):
                candidate.cost_ = cand_cost
                candidate.parent_ = node

    # chech if goal is in goal_radius
    def check_goal(self, node):
        distance = np.linalg.norm([node.x_ - self.goal_.x_, node.y_ - self.goal_.y_])
        if distance < self.goal_radius_:
            return True
        else:
            return False

    # generate path from give node to start and reverse
    def generate_path(self, node):
        path = []
        current_node = node
        while current_node is not None:
            path.append([current_node.x_, current_node.y_])
            current_node = current_node.parent_
        reversed_path = path[::-1]
        return reversed_path
    
    # main loop of algoritm
    def plan(self):
        for i in range(self.max_ierations_):
            # generate new node and move in its direction
            random_node = self.generate_node()
            nearest_node = self.get_nearest_node(random_node)
            new_node = self.steer(nearest_node, random_node)

            #if no collision then add to treee and try to optimize connections
            if not self.check_collision(new_node):
                neighbors = self.find_neighbors(new_node)
                new_node = self.choose_parent(neighbors, nearest_node, new_node)
                self.node_list_.append(new_node)
                self.rewire(neighbors, new_node)

            # return path if near goal
            if self.check_goal(new_node):
                self.path_ = self.generate_path(new_node)
                self.goal_reached_ = True
                return
    
    def update_state(self, new_start, new_goal, new_obstacles):
        self.start_ = Node(new_start[0], new_start[1])
        self.goal_ = Node(new_goal[0], new_goal[1])
        self.obstacles_ = new_obstacles
        self.node_list_ = [self.start_]
        self.path_ = None
        self.goal_reached_ = False
    
    def increase_iterations(self):
        self.max_ierations_ = math.ceil(1.2*self.max_ierations_)