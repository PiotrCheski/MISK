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
    def __init__(self, start, goal, obstacle_list):
        # wspólne parametry dla rrt*, będą stałe w symulacji, należy je dobrać do środowiska
        config_path = os.path.join(os.path.dirname(__file__), "rrt_star_config.yaml")
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        self.map_size_ = config['map_size']
        self.step_size_ = config['step_size']
        self.max_ierations_ = config['max_ierations']
        self.generate_chance_ = config['generate_chance']
        self.search_radius_ = config['search_radius']
        self.goal_radius_ = config['goal_radius']
        # parametry indywidalne dla każdego łazika
        self.start_ = Node(start[0], start[1])
        self.goal_ = Node(goal[0], goal[1])
        self.obstacles_ = obstacle_list
        self.node_list_ = [self.start_]
        self.path_ = None
        self.goal_reached_ = False

    def generate_node(self):
        # wylosuj node w przestrzeni (szansa na wylosowanie celu)
        if random.randint(0, 1) > self.generate_chance_:
            new_node = Node(random.uniform(0, self.map_size_[0]), random.uniform(0, self.map_size_[1]))
        else:
            new_node = self.goal_
        return new_node

    def get_nearest_node(self, target_node):
        # znajdź w drzewie node najbliżej do podanego
        distances = []
        for candidate in self.node_list_:
            distances.append(np.linalg.norm([target_node.x_ - candidate.x_, target_node.y_ - candidate.y_]))
        nearest_node = self.node_list_[np.argmin(distances)]
        return nearest_node
    
    def steer(self, from_node, target_node):
        # wygeneruj node w kierunku podanego
        # wyznaczenie kierunku
        theta = math.atan2(target_node.y_ - from_node.y_, target_node.x_ - from_node.x_)
        # wykonaj krok o step_size w tym kierunku, aktualizuj koszt
        new_node = Node(from_node.x_ + self.step_size_ * math.cos(theta), from_node.y_ + self.step_size_ * math.sin(theta))
        new_node.cost_ = from_node.cost_ + self.step_size_
        new_node.parent_ = from_node
        return new_node

    def check_collision(self, node):
        # sprawdź czy nie ma kolizji z przeszkodami
        for obstacle in self.obstacles_:
            distance = np.linalg.norm([node.x_ - obstacle[0], node.y_ - obstacle[1]])
            if distance <= obstacle[2]:
                return True
        return False

    def find_neighbors(self, node):
        # znajdź nody w otoczeniu podanego (search_radius)
        neighbors = []
        for candidate in self.node_list_:
            distance = np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if distance <= self.search_radius_:
                neighbors.append(candidate)
        return neighbors 

    def choose_parent(self, neighbors, closest_node, node):
        # wyznacz noda z którym będzie połączony podany
        min_cost = closest_node.cost_ + np.linalg.norm([node.x_ - closest_node.x_, node.y_ - closest_node.y_])
        best_node = closest_node
        # sprawdzenie czy w sąsiadach nie ma lepszej opcji
        for candidate in neighbors:
            cand_cost = candidate.cost_ + np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if (cand_cost < min_cost) and not self.check_collision(candidate):
                min_cost = cand_cost
                best_node = candidate
        node.cost_ = min_cost
        node.parent_ = best_node
        return node

    def rewire(self, neighbors, node):
        # sprawdż czy nie da się lepiej połączyć nodów (nowy node jako rodzic obecnego) (tych w promieniu)
         for candidate in neighbors:
            cand_cost = node.cost_ + np.linalg.norm([node.x_ - candidate.x_, node.y_ - candidate.y_])
            if (cand_cost < candidate.cost_) and not self.check_collision(candidate):
                candidate.cost_ = cand_cost
                candidate.parent_ = node

    def check_goal(self, node):
        # sprawdź czy cel osiągnięty (goal_radius)
        distance = np.linalg.norm([node.x_ - self.goal_.x_, node.y_ - self.goal_.y_])
        if distance < self.goal_radius_:
            return True
        else:
            return False

    def generate_path(self, node):
        # wygeneruj ścieżkę od podanego node do początku
        path = []
        current_node = node
        while current_node is not None:
            path.append([current_node.x_, current_node.y_])
            current_node = current_node.parent_
        reversed_path = path[::-1]
        return reversed_path
    
    def plan(self):
        # główna pętla działania algorytmu
        for i in range(self.max_ierations_):
            # wygeneruj node i porusz się w jego kierunku
            random_node = self.generate_node()
            nearest_node = self.get_nearest_node(random_node)
            new_node = self.steer(nearest_node, random_node)

            # jeśli nie ma kolizji to dodaj go do drzewa i zoptymalizuj je
            if not self.check_collision(new_node):
                neighbors = self.find_neighbors(new_node)
                new_node = self.choose_parent(neighbors, nearest_node, new_node)
                self.node_list_.append(new_node)
                self.rewire(neighbors, new_node)

            # jeśli jest w okolicy celu to zwróć ścieżkę
            if self.check_goal(new_node):
                self.path_ = self.generate_path(new_node)
                self.goal_reached_ = True
                return