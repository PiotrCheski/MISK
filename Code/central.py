import json
import time
import threading
import random
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.rrt_star_visualise import visualise_obstacles
from Code.area import Area

# Stałe konfiguracyjne dla Centrali
CRITICAL_HUMIDITY = 40.0
CRITICAL_PH_LOW = 5.8
CRITICAL_PH_HIGH = 8.2
MAX_SECONDS_SINCE_LAST_VISIT = 300
FIELD_RADIUS_FOR_OBSTACLES = 0.7
ROVER_RADIUS_FOR_OBSTACLES = 0.5

class Centrala:
    # Dodany parametr start_with_mapping_phase
    def __init__(self, sim_client, start_with_mapping_phase=False):
        self.sim = sim_client.require('sim')
        self.fields = {}
        self.rovers = {}
        self.task_queue = []
        self.obstacle_list = []
        
        self.running = True
        self.next_task_id = 0

        # Nowa flaga dla fazy mapowania
        self.mapping_phase_active = start_with_mapping_phase
        self.initial_mapping_tasks_generated = False # Pomocnicza flaga

        print("[Centrala] Inicjalizacja...")
        if self.mapping_phase_active:
            print("[Centrala] Rozpoczynam w fazie mapowania. Pola nie będą ładowane ze sceny.")
            # Przeszkody statyczne (np. granice mapy, znane stałe obiekty) można by tu zainicjować, jeśli są
            # self._initialize_static_obstacles() # Może być pusta lub ładować tylko granice
        else:
            print("[Centrala] Rozpoczynam w normalnym trybie operacyjnym.")
            self._load_fields_from_scene()
            self._initialize_static_obstacles() # Dodanie załadowanych pól do listy przeszkód

        self.simulation_thread = threading.Thread(target=self._main_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        print("[Centrala] Główna pętla uruchomiona.")

    def _get_new_task_id(self):
        self.next_task_id += 1
        return self.next_task_id

    def _load_fields_from_scene(self):
        print("[Centrala] Ładowanie informacji o polach...")
        index = 0
        while True:
            name = f"Field_{index}"
            try:
                handle = self.sim.getObjectHandle(name)
                if handle == -1:
                    if index == 0:
                        print(f"[Centrala] Błąd krytyczny: Nie znaleziono obiektu {name}. Upewnij się, że scena jest załadowana i pola są wygenerowane przez 'prepare_sim.py'.")
                    break 

                pos_raw = self.sim.getObjectPosition(handle, -1)
                pos = (round(pos_raw[0],3), round(pos_raw[1],3), round(pos_raw[2],3))
                data_raw = self.sim.readCustomDataBlock(handle, "SoilData")

                if not data_raw:
                    print(f"[Centrala] Ostrzeżenie: Brak danych SoilData dla {name}. Pomijam.")
                    index += 1
                    continue
                
                data_str = None
                if isinstance(data_raw, bytes):
                    try:
                        data_str = data_raw.decode('utf-8')
                    except UnicodeDecodeError:
                        print(f"[Centrala] Błąd: Nie udało się zdekodować bytes z SoilData (UTF-8) dla {name}. Dane: {data_raw}")
                        index += 1
                        continue
                elif isinstance(data_raw, str):
                    data_str = data_raw
                else:
                    print(f"[Centrala] Błąd: Nieoczekiwany typ danych dla SoilData dla {name}: {type(data_raw)}. Dane: {data_raw}")
                    index += 1
                    continue

                if data_str is None: 
                    index +=1
                    continue
                    
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    print(f"[Centrala] Błąd: Nie udało się zdekodować JSON z SoilData dla {name}. Zdekodowane dane: {data_str}")
                    index += 1
                    continue

                area_obj = Area(
                    pos[0], pos[1], pos[2],
                    data["humidity"],
                    data["pH"],
                    data["microbiome"],
                    data["temperature"],
                    data["minerals"],
                    name=name,                       
                    handle=handle,                   
                    last_visited_time=time.time()    
                )

                self.fields[name] = area_obj
                print(f"[Centrala] Załadowano {name} na ({area_obj.x}, {area_obj.y})")
                index += 1
            except Exception as e:
                print(f"[Centrala] Zakończono wyszukiwanie pól lub wystąpił błąd przy ładowaniu {name}: {e}")
                break
        if not self.fields:
            print("[Centrala] UWAGA: Nie załadowano żadnych pól. Dalsze działanie może być niemożliwe.")
        else:
            print(f"[Centrala] Załadowano {len(self.fields)} pól.")


    def _initialize_static_obstacles(self):
        self.obstacle_list = [] # Resetuj listę
        for field_name, area_obj in self.fields.items():
            self.obstacle_list.append({'x': area_obj.x, 'y': area_obj.y, 'radius': FIELD_RADIUS_FOR_OBSTACLES, 'type': 'field', 'id': field_name})
        print(f"[Centrala] Zainicjalizowano {len(self.obstacle_list)} statycznych przeszkód (pola).")
        # Można tu dodać inne statyczne przeszkody, np. granice mapy
        # self.obstacle_list.append({'x': 0, 'y': 10, 'radius': 1, 'type': 'border', 'id': 'border_north'})
        # self.obstacle_list.append({'x': 0, 'y': -10, 'radius': 1, 'type': 'border', 'id': 'border_south'})
        # self.obstacle_list.append({'x': 10, 'y': 0, 'radius': 1, 'type': 'border', 'id': 'border_east'})
        # self.obstacle_list.append({'x': -10, 'y': 0, 'radius': 1, 'type': 'border', 'id': 'border_west'})


    def _update_rover_obstacle_position(self, rover_id, new_x, new_y):
        found = False
        for obs in self.obstacle_list:
            if obs.get('type') == 'rover' and obs.get('id') == rover_id:
                obs['x'] = new_x
                obs['y'] = new_y
                found = True
                break
        if not found:
            self.obstacle_list.append({'x': new_x, 'y': new_y, 'radius': ROVER_RADIUS_FOR_OBSTACLES, 'type': 'rover', 'id': rover_id})

    def get_current_obstacle_list_for_rover(self, requesting_rover_id):
        obs_for_planner = []
        for obs in self.obstacle_list:
            if obs.get('type') == 'rover' and obs.get('id') == requesting_rover_id:
                continue 
            obs_for_planner.append((obs['x'], obs['y'], obs['radius']))
        return obs_for_planner

    def register_rover(self, rover_id, rover_object_instance, rover_state_instance, initial_position):
        if rover_id not in self.rovers:
            self.rovers[rover_id] = {
                'object': rover_object_instance, 
                'state_manager': rover_state_instance, 
                'status': 'idle', 
                'position': initial_position,
                'current_task_id': None,
                'current_task_target_field_name': None, 
                'task_queue_len': 0 
            }
            self._update_rover_obstacle_position(rover_id, initial_position[0], initial_position[1])
            print(f"[Centrala] Łazik {rover_id} zarejestrowany na pozycji {initial_position}.")
        else:
            print(f"[Centrala] Łazik {rover_id} jest już zarejestrowany.")

    def update_rover_info(self, rover_id, position, status, battery_level, task_queue_len=0):
        if rover_id in self.rovers:
            self.rovers[rover_id]['position'] = position
            self.rovers[rover_id]['status'] = status 
            self.rovers[rover_id]['battery_level'] = battery_level 
            self.rovers[rover_id]['task_queue_len'] = task_queue_len 
            self._update_rover_obstacle_position(rover_id, position[0], position[1])
        else:
            print(f"[Centrala] Ostrzeżenie: Próba aktualizacji info dla niezarejestrowanego łazika {rover_id}")
            
    def request_new_task_for_rover(self, rover_id):
        if not self.task_queue:
            return None 

        if rover_id not in self.rovers or self.rovers[rover_id]['status'] not in ['idle', 'returning']: 
            # print(f"[Centrala] Łazik {rover_id} nie jest gotowy na nowe zadanie (status: {self.rovers[rover_id].get('status', 'NIEZNANY')}).")
            return None

        # Prosta logika FIFO, można by dodać priorytetyzację zadań eksploracyjnych, jeśli są wymieszane
        task_to_assign = self.task_queue.pop(0) 
        
        self.rovers[rover_id]['current_task_id'] = task_to_assign['id']
        self.rovers[rover_id]['current_task_target_field_name'] = task_to_assign['field_name'] 
        self.rovers[rover_id]['status'] = 'assigned_task'
        
        target_field_obj = self.fields.get(task_to_assign['field_name'])
        if not target_field_obj and task_to_assign['type'] != 'explore_point': 
            print(f"[Centrala] Błąd: Pole {task_to_assign['field_name']} dla zadania {task_to_assign['id']} nie istnieje!")
            self.task_queue.insert(0, task_to_assign) 
            self.rovers[rover_id]['current_task_id'] = None
            self.rovers[rover_id]['current_task_target_field_name'] = None 
            self.rovers[rover_id]['status'] = 'idle'
            return None
        
        if task_to_assign['type'] != 'explore_point': 
            task_to_assign['target_coords'] = (target_field_obj.x, target_field_obj.y, target_field_obj.z)
        
        print(f"[Centrala] Przypisano zadanie {task_to_assign['id']} ({task_to_assign['type']} dla {task_to_assign.get('field_name', task_to_assign.get('details',{}).get('target_coords_explore'))}) do łazika {rover_id}.")
        return task_to_assign

    def report_task_completed(self, rover_id, task_id, success, field_data_after_work=None):
        if rover_id not in self.rovers:
            print(f"[Centrala] Niezarejestrowany łazik {rover_id} próbuje raportować zadanie.")
            return

        rover_info = self.rovers[rover_id]
        if rover_info['current_task_id'] != task_id:
            print(f"[Centrala] Łazik {rover_id} raportuje zadanie {task_id}, ale oczekiwano {rover_info['current_task_id']}.")
            # Jeśli łazik raportuje stare zadanie, a już ma nowe lub jest idle,
            # po prostu ustawmy go na idle, jeśli nie jest, i wyczyśćmy dane zadania
            if rover_info['status'] != 'idle':
                rover_info['status'] = 'idle'
            # Nie czyścimy current_task_id, jeśli jest już inne - to by było dziwne
            # Można by dodać logikę, że jeśli task_id jest stare, to ignorujemy raport, ale ważne żeby łazik mógł przejść do idle
            return # Zmienione: nie czyść current_task_id jeśli nie pasuje, pozwól łazikowi samemu przejść do idle

        print(f"[Centrala] Łazik {rover_id} raportuje ukończenie zadania {task_id} (sukces: {success}).")
        original_task_type = "unknown" # Spróbujmy znaleźć typ oryginalnego zadania
        # Szukanie zadania po ID - to jest trochę obejście, bo zadanie znika z kolejki.
        # Lepiej by było, gdyby łazik sam przesyłał typ zadania.
        # Na potrzeby logiki ponownego dodania `explore_point` to wystarczy
        temp_task_details = self.rovers[rover_id].get('object').current_task # Zakładamy, że łazik trzyma szczegóły
        if temp_task_details and temp_task_details.get('id') == task_id:
            original_task_type = temp_task_details.get('type')

        rover_info['status'] = 'idle' 
        rover_info['current_task_id'] = None
        rover_info['current_task_target_field_name'] = None 

        if success and field_data_after_work:
            field_name = field_data_after_work.get('name')
            if field_name and field_name in self.fields:
                field_obj = self.fields[field_name]
                field_obj.humidity = field_data_after_work.get('humidity', field_obj.humidity)
                field_obj.pH = field_data_after_work.get('pH', field_obj.pH)
                field_obj.microbiome = field_data_after_work.get('microbiome', field_obj.microbiome)
                field_obj.temperature = field_data_after_work.get('temperature', field_obj.temperature)
                minerals_key = 'minerals' if 'minerals' in field_data_after_work else 'mineral_composition'
                field_obj.mineral_composition = field_data_after_work.get(minerals_key, field_obj.mineral_composition)
                field_obj.last_visited_time = time.time()
                print(f"[Centrala] Zaktualizowano parametry dla pola {field_name} po pracy łazika {rover_id}.")
                
                soil_data_to_write = {
                    "area": (field_obj.x, field_obj.y, field_obj.z),
                    "humidity": field_obj.humidity,
                    "pH": field_obj.pH,
                    "microbiome": field_obj.microbiome,
                    "temperature": field_obj.temperature,
                    "minerals": field_obj.mineral_composition 
                }
                try:
                    if field_obj.handle != -1: 
                         self.sim.writeCustomDataBlock(field_obj.handle, "SoilData", json.dumps(soil_data_to_write).encode('utf-8'))
                except Exception as e:
                    print(f"[Centrala] Błąd podczas zapisu CustomDataBlock dla {field_name}: {e}")
            # else: # To nie błąd, jeśli field_data_after_work dotyczyło np. 'explore_point'
            #     print(f"[Centrala] Ostrzeżenie: Nie można zaktualizować danych pola {field_name} - brak w rejestrze.")
        elif not success:
            print(f"[Centrala] Zadanie {task_id} ({original_task_type}) nie powiodło się dla łazika {rover_id}.")
            # Jeśli zadanie eksploracji nie powiodło się, można je dodać z powrotem do kolejki
            if self.mapping_phase_active and original_task_type == 'explore_point' and temp_task_details:
                # Sprawdź, czy zadanie o tym samym celu już nie wróciło do kolejki
                # (np. jeśli łazik sam sobie je dodał, co nie powinno mieć miejsca)
                # lub jeśli nie ma limitu prób
                # Na razie prosto: dodaj z powrotem na koniec kolejki
                print(f"[Centrala] Dodaję nieudane zadanie eksploracji {task_id} z powrotem do kolejki.")
                # Musimy odtworzyć zadanie, bo zostało usunięte z task_queue
                # Idealnie, `temp_task_details` to całe zadanie
                # Upewnijmy się, że to nie jest zduplikowane ID
                # Lepsze podejście: centrala powinna trzymać kopię przypisanych zadań
                # Na razie: nie dodajemy z powrotem automatycznie, aby uniknąć pętli.
                # Łazik powinien zgłosić, dlaczego się nie udało. Centrala może potem podjąć decyzję.
                pass


    def _main_loop(self):
        while self.running:
            current_time = time.time()

            # Logika dla fazy mapowania
            if self.mapping_phase_active:
                if not self.initial_mapping_tasks_generated:
                    self.initiate_remapping_procedure() # Użyj tej samej funkcji do generowania zadań eksploracji
                    self.initial_mapping_tasks_generated = True
                
                # Sprawdź, czy faza mapowania dobiegła końca
                no_explore_tasks_in_queue = not any(task['type'] == 'explore_point' for task in self.task_queue)
                no_rovers_exploring = not any(
                    rover_info.get('current_task_id') and
                    # Potrzebujemy dostępu do typu zadania, które łazik wykonuje
                    # Załóżmy, że łazik przechowuje `current_task` i możemy to odpytać (lub centrala trzyma kopię)
                    # Prostsze: jeśli `current_task_target_field_name` zaczyna się od "explore_point_"
                    (rover_info.get('current_task_target_field_name', '').startswith("explore_point_"))
                    for rover_info in self.rovers.values()
                )

                if no_explore_tasks_in_queue and no_rovers_exploring and self.initial_mapping_tasks_generated : # Upewnij się, że zadania były wygenerowane
                    if not self.fields: # Jeśli po mapowaniu nie ma żadnych pól, coś poszło nie tak.
                        print("[Centrala] Faza mapowania zakończona, ale nie odkryto żadnych pól. Sprawdź logi łazików i detekcję markerów.")
                        # Można by spróbować ponownie, albo zatrzymać, albo przejść do trybu czuwania.
                        # Na razie przechodzimy dalej, ale z ostrzeżeniem.
                    else:
                        print(f"[Centrala] Faza mapowania zakończona. Odkryto {len(self.fields)} pól. Wyświetlam pozycje na mapie.")
                        temp_counter = 0
                        for field in self.fields:
                            print(f"[Centrala] Pole: {field.name} na pozycji: {field.x},{field.y}")
                            visualise_obstacles(self.sim, [field.x, field.y], temp_counter)
                            temp_counter+=1
                    self.mapping_phase_active = False
                    self.initial_mapping_tasks_generated = False # Reset na wypadek ponownego mapowania
                    print("[Centrala] Koniec scenariusza.")
                    return
                    # Po zakończeniu mapowania, można zainicjalizować przeszkody na nowo,
                    # jeśli `report_discovered_field` nie dodawał ich dynamicznie.
                    # Ale obecna `report_discovered_field` dodaje, więc to jest OK.
                    # self._initialize_static_obstacles() # Jeśli przeszkody nie były dodawane na bieżąco
            
            else: # Normalny tryb operacyjny (nie faza mapowania)
                # 1. Symulacja degradacji parametrów pól (tylko jeśli są pola)
                if self.fields:
                    for field_name, field_obj in self.fields.items():
                        if field_obj.handle != -1: 
                            field_obj.humidity = max(0, round(field_obj.humidity - 0.05, 2)) 
                            field_obj.pH = round(field_obj.pH + random.uniform(-0.01, 0.01), 2) 
                
                # 2. Generowanie zadań utrzymania
                self._generate_tasks(current_time)
            
            time.sleep(2) 

    def _generate_tasks(self, current_time):
        # Nie generuj zadań utrzymania podczas fazy mapowania
        if self.mapping_phase_active:
            return

        if not self.fields: # Jeśli nie ma pól, nie ma co generować zadań utrzymania
            return

        for field_name, field_obj in self.fields.items():
            # Sprawdź, czy już istnieje aktywne zadanie lub zadanie w kolejce dla tego pola
            task_in_queue_for_field = any(
                task['field_name'] == field_name for task in self.task_queue
            )
            
            task_assigned_to_rover_for_field = any(
                # Sprawdzamy, czy current_task_target_field_name łazika pasuje
                # ORAZ czy łazik faktycznie ma przypisane zadanie (current_task_id is not None)
                rover_info.get('current_task_target_field_name') == field_name and
                rover_info.get('current_task_id') is not None # Dodatkowe zabezpieczenie
                for rover_info in self.rovers.values()
            )

            if task_in_queue_for_field or task_assigned_to_rover_for_field:
                # print(f"[Centrala DEBUG] Zadanie dla {field_name} już w kolejce lub przypisane. Pomijam generowanie nowego.")
                continue

            # Zadanie: Niska wilgotność
            if field_obj.humidity < CRITICAL_HUMIDITY:
                task_details = {'target_humidity': random.uniform(60,75)} # Docelowa wilgotność
                self.add_task_to_queue(field_name, 'restore_humidity', task_details, priority=1) # Normalny priorytet
                continue # Jedno zadanie na pole na cykl generowania

            # Zadanie: Nieprawidłowe pH
            if field_obj.pH < CRITICAL_PH_LOW or field_obj.pH > CRITICAL_PH_HIGH:
                target_ph = 7.0 # Dążymy do neutralnego
                task_details = {'target_pH': target_ph}
                self.add_task_to_queue(field_name, 'adjust_pH', task_details, priority=1)
                continue
            
            # Zadanie: Wizyta kontrolna z powodu długiego braku odwiedzin
            if (current_time - field_obj.last_visited_time) > MAX_SECONDS_SINCE_LAST_VISIT:
                self.add_task_to_queue(field_name, 'visit_scan', {}, priority=2) # Niższy priorytet dla skanowania
                continue
    
    def add_task_to_queue(self, field_name, task_type, details, priority=1):
        new_task_id = self._get_new_task_id()
        task = {
            'id': new_task_id,
            'field_name': field_name, 
            'type': task_type,
            'details': details,
            'priority': priority,
            'status': 'queued', 
            'added_time': time.time()
        }
        
        target_description = field_name
        if task_type == 'explore_point' and 'target_coords_explore' in details:
            target_description = f"punktu eksploracji {details['target_coords_explore']}"

        self.task_queue.append(task)
        # Sortowanie kolejki po priorytecie (mniejsza wartość = wyższy priorytet)
        self.task_queue.sort(key=lambda t: t.get('priority', 1))
        print(f"[Centrala] Dodano zadanie {new_task_id} ({task_type}, prio: {priority}) dla {target_description} do kolejki. Długość kolejki: {len(self.task_queue)}")


    def initiate_remapping_procedure(self):
        print("[Centrala] Inicjacja procedury generowania zadań eksploracyjnych...")
        # Parametry siatki eksploracji
        min_x, max_x = -4, 4 
        min_y, max_y = -4, 4
        step = 0.5 # Rozmiar "oczek" siatki

        # Usuń stare zadania typu 'explore_point' (jeśli są, na wypadek ponownego mapowania)
        # Ale tylko jeśli to nie jest pierwsze generowanie w fazie mapowania
        if not (self.mapping_phase_active and not self.initial_mapping_tasks_generated):
            self.task_queue = [t for t in self.task_queue if t.get('type') != 'explore_point']

        num_explore_tasks = 0
        for x_coord in [round(i * step,2) for i in range(int(min_x / step), int(max_x / step) + 1)]:
            for y_coord in [round(j * step,2) for j in range(int(min_y / step), int(max_y / step) + 1)]:
                # Sprawdź, czy w pobliżu tego punktu nie ma już znanego pola (jeśli już jakieś istnieją)
                too_close_to_known_field = False
                if self.fields: # Sprawdzaj tylko, jeśli już są jakieś pola
                    for field_obj in self.fields.values():
                        if math.hypot(field_obj.x - x_coord, field_obj.y - y_coord) < step * 0.75: 
                            too_close_to_known_field = True
                            break
                if too_close_to_known_field:
                    continue
                # punkt nie może być w miejscu centrali
                if (x_coord>-0.4 and x_coord<0.4) and (y_coord>-0.4 and y_coord<0.4):
                    continue

                details = {'target_coords_explore': (x_coord, y_coord, 0.25)} # Wysokość Z do ustawienia
                # Nazwa pola dla zadań eksploracyjnych może być generowana
                pseudo_field_name = f"explore_point_{x_coord:.1f}_{y_coord:.1f}"
                # Sprawdź, czy zadanie o tym samym celu (pseudo_field_name) już nie jest w kolejce
                if any(t['field_name'] == pseudo_field_name and t['type'] == 'explore_point' for t in self.task_queue):
                    continue

                self.add_task_to_queue(pseudo_field_name, 'explore_point', details, priority=0) # Wyższy priorytet (0)
                num_explore_tasks +=1
        
        if num_explore_tasks > 0:
            print(f"[Centrala] Dodano {num_explore_tasks} zadań eksploracyjnych do kolejki.")
        else:
            print(f"[Centrala] Nie dodano nowych zadań eksploracyjnych (być może wszystkie punkty są blisko znanych pól lub siatka jest pusta).")


    def report_discovered_field(self, rover_id, marker_id, detected_position_world, field_parameters_from_scan):
        discovered_field_name = f"Field_{marker_id}" 

        if discovered_field_name in self.fields:
            print(f"[Centrala] Łazik {rover_id} zgłosił pole {discovered_field_name}, które już jest znane. Aktualizacja pozycji/danych.")
            field_obj = self.fields[discovered_field_name]
            field_obj.x, field_obj.y, field_obj.z = detected_position_world
            field_obj.humidity = field_parameters_from_scan.get('humidity', field_obj.humidity)
            field_obj.pH = field_parameters_from_scan.get('pH', field_obj.pH)
            field_obj.last_visited_time = time.time()
            
            found_in_obstacles = False
            for obs in self.obstacle_list:
                if obs.get('type') == 'field' and obs.get('id') == discovered_field_name:
                    obs['x'], obs['y'] = detected_position_world[0], detected_position_world[1]
                    found_in_obstacles = True
                    break
            if not found_in_obstacles:
                 self.obstacle_list.append({'x': detected_position_world[0], 'y': detected_position_world[1], 'radius': FIELD_RADIUS_FOR_OBSTACLES, 'type': 'field', 'id': discovered_field_name})
        else:
            print(f"[Centrala] Łazik {rover_id} odkrył NOWE pole {discovered_field_name} (marker: {marker_id}) na {detected_position_world}!")
            
            # Sprawdzenie, czy obiekt o tej nazwie już istnieje w symulacji (np. z poprzedniego uruchomienia, ale nie w self.fields)
            existing_handle = self.sim.getObjectHandle(discovered_field_name)
            if existing_handle != -1:
                print(f"[Centrala] Uwaga: Obiekt {discovered_field_name} już istnieje w symulacji, ale nie był w rejestrze. Używam istniejącego uchwytu.")
                handle_for_new_field = existing_handle
                # Można by zaktualizować jego pozycję w symulacji, jeśli się różni
                # self.sim.setObjectPosition(handle_for_new_field, -1, detected_position_world)
            else:
                # Opcjonalnie: Stwórz obiekt w symulacji
                print(f"[Centrala] Tworzenie nowego obiektu '{discovered_field_name}' w symulacji...")
                try:
                    # Przykładowo: stwórz sześcian reprezentujący pole
                    # Rozmiary i typ do dostosowania
                    shape_handle = self.sim.createPrimitiveShape(self.sim.primitiveshape_cuboid, [0.5, 0.5, 0.1]) # sizeX, sizeY, sizeZ
                    self.sim.setObjectAlias(shape_handle, discovered_field_name)
                    self.sim.setObjectPosition(shape_handle, -1, detected_position_world)
                    # Ustaw właściwości wizualne, np. kolor
                    self.sim.setShapeColor(shape_handle, None, self.sim.colorcomponent_ambient_diffuse, [0.2, 0.6, 0.2]) # RGB zielonkawy
                    handle_for_new_field = shape_handle
                    print(f"[Centrala] Stworzono obiekt {discovered_field_name} w symulacji z uchwytem {handle_for_new_field}.")
                except Exception as e:
                    print(f"[Centrala] Błąd podczas tworzenia obiektu {discovered_field_name} w symulacji: {e}")
                    handle_for_new_field = -1 # Nie udało się stworzyć obiektu

            new_area_obj = Area(
                detected_position_world[0], detected_position_world[1], detected_position_world[2],
                field_parameters_from_scan.get('humidity', 50),
                field_parameters_from_scan.get('pH', 7.0),
                field_parameters_from_scan.get('microbiome', "Unknown"),
                field_parameters_from_scan.get('temperature', 20.0),
                field_parameters_from_scan.get('minerals', "Unknown"),
                name=discovered_field_name,       
                handle=handle_for_new_field, # Użyj uchwytu stworzonego obiektu lub -1                
                last_visited_time=time.time()     
            )
            self.fields[discovered_field_name] = new_area_obj
            
            # Zapisz dane SoilData do nowego obiektu w symulacji, jeśli został stworzony
            if handle_for_new_field != -1:
                soil_data_to_write = {
                    "area": (new_area_obj.x, new_area_obj.y, new_area_obj.z),
                    "humidity": new_area_obj.humidity,
                    "pH": new_area_obj.pH,
                    "microbiome": new_area_obj.microbiome,
                    "temperature": new_area_obj.temperature,
                    "minerals": new_area_obj.mineral_composition
                }
                try:
                    self.sim.writeCustomDataBlock(handle_for_new_field, "SoilData", json.dumps(soil_data_to_write).encode('utf-8'))
                    print(f"[Centrala] Zapisano SoilData dla nowego pola {discovered_field_name}.")
                except Exception as e:
                    print(f"[Centrala] Błąd podczas zapisu SoilData dla nowego pola {discovered_field_name}: {e}")

            # Dodaj jako przeszkodę
            self.obstacle_list.append({'x': new_area_obj.x, 'y': new_area_obj.y, 'radius': FIELD_RADIUS_FOR_OBSTACLES, 'type': 'field', 'id': discovered_field_name})
            print(f"[Centrala] Dodano nowe pole {discovered_field_name} do rejestru i listy przeszkód.")


    def stop(self):
        print("[Centrala] Zatrzymywanie...")
        self.running = False
        if self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5) 
        print("[Centrala] Zatrzymana.")