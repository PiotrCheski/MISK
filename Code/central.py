import json
import time
import threading
import random
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient # Zakładamy, że jest dostępne
# Ścieżki do twoich modułów - dostosuj, jeśli struktura folderów jest inna
# Np. jeśli area.py jest w folderze 'Code' na tym samym poziomie co 'central.py'
# import sys
# import os
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Code')) # lub odpowiednia ścieżka
from Code.area import Area # Zakładamy, że jest w PYTHONPATH lub tym samym katalogu

# Stałe konfiguracyjne dla Centrali
CRITICAL_HUMIDITY = 40.0
CRITICAL_PH_LOW = 5.8
CRITICAL_PH_HIGH = 8.2 # Można też dodać górne granice
MAX_SECONDS_SINCE_LAST_VISIT = 300 # 5 minut
FIELD_RADIUS_FOR_OBSTACLES = 0.7 # Promień pola jako przeszkody (nieco większy niż rozmiar)
ROVER_RADIUS_FOR_OBSTACLES = 0.5 # Promień łazika jako przeszkody

class Centrala:
    def __init__(self, sim_client):
        self.sim = sim_client.require('sim')
        self.fields = {}  # Słownik: {field_name: Area_object}
        self.rovers = {}  # Słownik: {rover_id: {'object': RoverObject, 'state': RoverState_instance, 'status': 'idle'/'busy'/'charging', 'position': (x,y,z), 'current_task': None}}
        self.task_queue = [] # Lista zadań: [{'id': taskId, 'field_name': str, 'type': 'restore_humidity'/'visit_scan'/etc., 'details': {}, 'priority': 1}]
        self.obstacle_list = [] # Lista [(x, y, promień), ...] dla RRT*
        
        self.running = True
        self.next_task_id = 0

        print("[Centrala] Inicjalizacja...")
        self._load_fields_from_scene()
        self._initialize_static_obstacles() # Dodanie pól do listy przeszkód

        # Wątek do symulacji zmian w środowisku i zarządzania zadaniami
        self.simulation_thread = threading.Thread(target=self._main_loop)
        self.simulation_thread.daemon = True # Zakończ wątek, gdy główny program się zakończy
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

                if data_str is None: # Jeśli dekodowanie się nie powiodło lub był zły typ
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
        """Dodaje wszystkie pola jako statyczne przeszkody."""
        self.obstacle_list = []
        for field_name, area_obj in self.fields.items():
            #elf.obstacle_list.append({'x': area_obj.x, 'y': area_obj.y, 'radius': FIELD_RADIUS_FOR_OBSTACLES, 'type': 'field', 'id': field_name})
            pass
        print(f"[Centrala] Zainicjalizowano {len(self.obstacle_list)} statycznych przeszkód (pola).")

    def _update_rover_obstacle_position(self, rover_id, new_x, new_y):
        """Aktualizuje pozycję łazika na liście przeszkód lub dodaje go."""
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
        """Zwraca listę przeszkód (x,y,r) dla planera RRT*, pomijając samego łazika proszącego."""
        # print(f"[Centrala] Generowanie listy przeszkód dla {requesting_rover_id}. Pełna lista: {self.obstacle_list}")
        obs_for_planner = []
        for obs in self.obstacle_list:
            if obs.get('type') == 'rover' and obs.get('id') == requesting_rover_id:
                continue # Pomiń samego siebie
            obs_for_planner.append((obs['x'], obs['y'], obs['radius']))
        # print(f"[Centrala] Lista przeszkód dla {requesting_rover_id}: {obs_for_planner}")
        return obs_for_planner

    # --- Metody do interakcji z Łazikami ---
    def register_rover(self, rover_id, rover_object_instance, rover_state_instance, initial_position):
        if rover_id not in self.rovers:
            self.rovers[rover_id] = {
                'object': rover_object_instance, # Instancja klasy Rover
                'state_manager': rover_state_instance, # Instancja RoverState
                'status': 'idle', # Początkowy status
                'position': initial_position,
                'current_task_id': None,
                'task_queue_len': 0 # Jeśli łazik ma swoją kolejkę
            }
            self._update_rover_obstacle_position(rover_id, initial_position[0], initial_position[1])
            print(f"[Centrala] Łazik {rover_id} zarejestrowany na pozycji {initial_position}.")
        else:
            print(f"[Centrala] Łazik {rover_id} jest już zarejestrowany.")

    def update_rover_info(self, rover_id, position, status, battery_level, task_queue_len=0):
        if rover_id in self.rovers:
            self.rovers[rover_id]['position'] = position
            self.rovers[rover_id]['status'] = status # 'idle', 'moving', 'working', 'charging'
            self.rovers[rover_id]['battery_level'] = battery_level # Odczytane z RoverState
            self.rovers[rover_id]['task_queue_len'] = task_queue_len # Jeśli łazik ma swoją kolejkę
            self._update_rover_obstacle_position(rover_id, position[0], position[1])
            # print(f"[Centrala] Info dla {rover_id}: Poz: {position}, Status: {status}, Bateria: {battery_level}%")
        else:
            print(f"[Centrala] Ostrzeżenie: Próba aktualizacji info dla niezarejestrowanego łazika {rover_id}")
            
    def request_new_task_for_rover(self, rover_id):
        """Wywoływane przez łazika, gdy jest gotowy na nowe zadanie."""
        if not self.task_queue:
            return None # Brak zadań

        if rover_id not in self.rovers or self.rovers[rover_id]['status'] not in ['idle', 'returning']: # returning to by był stan po zakończeniu zadania
            print(f"[Centrala] Łazik {rover_id} nie jest gotowy na nowe zadanie (status: {self.rovers[rover_id].get('status', 'NIEZNANY')}).")
            return None

        # Prosta logika FIFO na razie, można rozbudować o priorytety
        task_to_assign = self.task_queue.pop(0) 
        
        self.rovers[rover_id]['current_task_id'] = task_to_assign['id']
        self.rovers[rover_id]['status'] = 'assigned_task' # Łazik musi potwierdzić przyjęcie i zmienić na 'moving'/'working'
        
        # Przekaż cel i szczegóły do łazika (bezpośrednie wywołanie metody łazika)
        target_field_obj = self.fields.get(task_to_assign['field_name'])
        if not target_field_obj:
            print(f"[Centrala] Błąd: Pole {task_to_assign['field_name']} dla zadania {task_to_assign['id']} nie istnieje!")
            self.task_queue.insert(0, task_to_assign) # Wróć zadanie
            self.rovers[rover_id]['current_task_id'] = None
            self.rovers[rover_id]['status'] = 'idle'
            return None

        task_to_assign['target_coords'] = (target_field_obj.x, target_field_obj.y, target_field_obj.z)
        
        print(f"[Centrala] Przypisano zadanie {task_to_assign['id']} ({task_to_assign['type']} dla {task_to_assign['field_name']}) do łazika {rover_id}.")
        return task_to_assign # Łazik otrzymuje szczegóły zadania

    def report_task_completed(self, rover_id, task_id, success, field_data_after_work=None):
        if rover_id not in self.rovers:
            print(f"[Centrala] Niezarejestrowany łazik {rover_id} próbuje raportować zadanie.")
            return

        if self.rovers[rover_id]['current_task_id'] != task_id:
            print(f"[Centrala] Łazik {rover_id} raportuje zadanie {task_id}, ale oczekiwano {self.rovers[rover_id]['current_task_id']}.")
            # Możliwe, że zadanie zostało anulowane lub przedawniło się. Na razie ignorujemy.
            # Ważne, aby łazik przeszedł w stan idle
            self.rovers[rover_id]['status'] = 'idle' 
            self.rovers[rover_id]['current_task_id'] = None
            return

        original_task = None
        # Znajdź oryginalne zadanie po ID - może być potrzebne jeśli zadanie zostało usunięte z kolejki
        # ale na razie zakładamy, że jeśli łazik je wykonuje, to zostało mu przypisane.
        
        print(f"[Centrala] Łazik {rover_id} raportuje ukończenie zadania {task_id} (sukces: {success}).")
        self.rovers[rover_id]['status'] = 'idle' # Łazik jest znów wolny
        self.rovers[rover_id]['current_task_id'] = None

        if success and field_data_after_work:
            field_name = field_data_after_work.get('name')
            if field_name and field_name in self.fields:
                field_obj = self.fields[field_name]
                field_obj.humidity = field_data_after_work.get('humidity', field_obj.humidity)
                field_obj.pH = field_data_after_work.get('pH', field_obj.pH)
                field_obj.microbiome = field_data_after_work.get('microbiome', field_obj.microbiome)
                field_obj.temperature = field_data_after_work.get('temperature', field_obj.temperature)
                field_obj.mineral_composition = field_data_after_work.get('mineral_composition', field_obj.mineral_composition)
                field_obj.last_visited_time = time.time()
                print(f"[Centrala] Zaktualizowano parametry dla pola {field_name} po pracy łazika {rover_id}.")
                
                # Zaktualizuj CustomDataBlock w symulacji
                soil_data_to_write = {
                    "area": (field_obj.x, field_obj.y, field_obj.z),
                    "humidity": field_obj.humidity,
                    "pH": field_obj.pH,
                    "microbiome": field_obj.microbiome,
                    "temperature": field_obj.temperature,
                    "minerals": field_obj.mineral_composition
                }
                try:
                    self.sim.writeCustomDataBlock(field_obj.handle, "SoilData", json.dumps(soil_data_to_write).encode('utf-8'))
                except Exception as e:
                    print(f"[Centrala] Błąd podczas zapisu CustomDataBlock dla {field_name}: {e}")
            else:
                print(f"[Centrala] Ostrzeżenie: Nie można zaktualizować danych pola {field_name} - brak w rejestrze.")
        elif not success:
            print(f"[Centrala] Zadanie {task_id} nie powiodło się dla łazika {rover_id}. Rozważ ponowne dodanie do kolejki.")
            # TODO: logika ponawiania zadań

    # --- Główna pętla symulacyjna Centrali ---
    def _main_loop(self):
        while self.running:
            current_time = time.time()
            
            # 1. Symulacja degradacji parametrów pól
            for field_name, field_obj in self.fields.items():
                # Prosta liniowa degradacja, można to uczynić bardziej złożonym
                field_obj.humidity = max(0, round(field_obj.humidity - 0.05, 2)) # spadek o 0.05 co cykl pętli
                field_obj.pH = round(field_obj.pH + random.uniform(-0.01, 0.01), 2) # drobne wahania pH
                # ... inne parametry
            
            # 2. Generowanie zadań
            self._generate_tasks(current_time)
            
            # 3. Przypisywanie zadań (już nie tutaj, łaziki same proszą)
            # self._assign_tasks_to_available_rovers()

            time.sleep(2) # Główny cykl centrali co 2 sekundy

    def _generate_tasks(self, current_time):
        for field_name, field_obj in self.fields.items():
            # Sprawdź, czy już istnieje aktywne zadanie lub zadanie w kolejce dla tego pola
            task_already_exists = any(
                task['field_name'] == field_name for task in self.task_queue
            ) or any(
                rover_info.get('current_task_id') and 
                self._get_task_details_by_id(rover_info['current_task_id']) and # upewnij się, że zadanie istnieje
                self._get_task_details_by_id(rover_info['current_task_id'])['field_name'] == field_name
                for rover_info in self.rovers.values()
            )

            if task_already_exists:
                continue

            # Zadanie: Niska wilgotność
            if field_obj.humidity < CRITICAL_HUMIDITY:
                task_details = {'target_humidity': random.uniform(60,75)} # Docelowa wilgotność
                self.add_task_to_queue(field_name, 'restore_humidity', task_details)
                continue # Jedno zadanie na pole na cykl generowania

            # Zadanie: Nieprawidłowe pH
            if field_obj.pH < CRITICAL_PH_LOW or field_obj.pH > CRITICAL_PH_HIGH:
                target_ph = 7.0 # Dążymy do neutralnego
                task_details = {'target_pH': target_ph}
                self.add_task_to_queue(field_name, 'adjust_pH', task_details)
                continue
            
            # Zadanie: Wizyta kontrolna z powodu długiego braku odwiedzin
            if (current_time - field_obj.last_visited_time) > MAX_SECONDS_SINCE_LAST_VISIT:
                self.add_task_to_queue(field_name, 'visit_scan', {})
                continue
    
    def _get_task_details_by_id(self, task_id):
        """Pomocnicza funkcja do znalezienia zadania w kolejce lub wśród przypisanych (potrzebne do _generate_tasks)."""
        # Ta funkcja jest trochę problematyczna, bo zadania znikają z task_queue po przypisaniu.
        # Dla uproszczenia, jeśli current_task_id jest ustawione, zakładamy, że zadanie jest aktywne.
        # Lepszym rozwiązaniem byłoby przechowywanie kopii przypisanych zadań.
        # Na potrzeby `_generate_tasks` wystarczy, że `current_task_id` jest nie-None.
        # Jeśli potrzebujemy szczegółów, łazik powinien je mieć.
        # To jest uproszczenie - w pełnym systemie moglibyśmy mieć słownik aktywnych zadań.
        for task in self.task_queue: # Sprawdź najpierw w kolejce
            if task['id'] == task_id:
                return task
        # Jeśli nie ma w kolejce, to znaczy, że jest przypisane, ale nie mamy tu jego pełnych danych.
        # _generate_tasks potrzebuje tylko wiedzieć, czy dla danego pola jest aktywne zadanie.
        return {'id': task_id, 'field_name': 'unknown_field_for_active_task'} # Placeholder

    def add_task_to_queue(self, field_name, task_type, details, priority=1):
        new_task_id = self._get_new_task_id()
        task = {
            'id': new_task_id,
            'field_name': field_name,
            'type': task_type,
            'details': details,
            'priority': priority,
            'status': 'queued', # queued, assigned, in_progress, completed, failed
            'added_time': time.time()
        }
        self.task_queue.append(task)
        print(f"[Centrala] Dodano zadanie {new_task_id} ({task_type}) dla {field_name} do kolejki.")

    def initiate_remapping_procedure(self):
        print("[Centrala] Inicjacja procedury re-mapowania (jeszcze nie zaimplementowane).")
        # 1. Określ granice mapy (np. z configu lub na podstawie istniejących pól)
        min_x, max_x = -7, 7 
        min_y, max_y = -7, 7
        step = 2.0 # Rozmiar "oczek" siatki do eksploracji

        # 2. Usuń stare zadania typu 'explore_point' (jeśli są)
        self.task_queue = [t for t in self.task_queue if t.get('type') != 'explore_point']

        # 3. Wygeneruj zadania eksploracji
        num_explore_tasks = 0
        for x_coord in [i * step for i in range(int(min_x / step), int(max_x / step) + 1)]:
            for y_coord in [j * step for j in range(int(min_y / step), int(max_y / step) + 1)]:
                # Sprawdź, czy w pobliżu tego punktu nie ma już znanego pola
                too_close_to_known_field = False
                for field_obj in self.fields.values():
                    if math.hypot(field_obj.x - x_coord, field_obj.y - y_coord) < step * 0.75: # Jeśli punkt jest blisko środka znanego pola
                        too_close_to_known_field = True
                        break
                if too_close_to_known_field:
                    continue

                details = {'target_coords_explore': (x_coord, y_coord, 0.25)} # Wysokość Z do ustawienia
                # Nazwa pola dla zadań eksploracyjnych może być generowana
                pseudo_field_name = f"explore_point_{x_coord:.1f}_{y_coord:.1f}"
                self.add_task_to_queue(pseudo_field_name, 'explore_point', details, priority=0) # Wyższy priorytet
                num_explore_tasks +=1
        print(f"[Centrala] Dodano {num_explore_tasks} zadań eksploracyjnych do kolejki.")


    def report_discovered_field(self, rover_id, marker_id, detected_position_world, field_parameters_from_scan):
        """Wywoływane przez łazika, gdy znajdzie marker podczas eksploracji."""
        # Upewnij się, że nazwa pola jest unikalna i oparta na marker_id
        discovered_field_name = f"Field_{marker_id}" # Zakładamy, że marker_id jest unikalne dla pola

        if discovered_field_name in self.fields:
            print(f"[Centrala] Łazik {rover_id} zgłosił pole {discovered_field_name}, które już jest znane. Aktualizacja pozycji/danych.")
            # Można zaktualizować pozycję, jeśli się różni, lub parametry.
            field_obj = self.fields[discovered_field_name]
            field_obj.x, field_obj.y, field_obj.z = detected_position_world
            # Aktualizacja parametrów:
            field_obj.humidity = field_parameters_from_scan.get('humidity', field_obj.humidity)
            # ... inne parametry ...
            field_obj.last_visited_time = time.time()
            # Upewnij się, że jest na liście przeszkód
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
            # "centrala najpierw musi zadać łazikowi ruch “gdzieś obok” żeby się odsunął zanim doda pole do przeszkód"
            # To jest trudne do zaimplementowania synchronicznie w tym modelu.
            # Możliwe podejście:
            # 1. Centrala notuje "potencjalne nowe pole".
            # 2. Wysyła specjalne polecenie łazikowi "move_away_from_discovery_point".
            # 3. Łazik wykonuje ten ruch i raportuje nową pozycję.
            # 4. Dopiero wtedy centrala formalnie dodaje pole do self.fields i obstacle_list.

            # Uproszczone podejście na teraz: dodajemy od razu, zakładając, że łazik i tak zaraz odjedzie.
            # Ryzyko: jeśli łazik zdecyduje się na następny ruch zanim centrala zaktualizuje przeszkody,
            # a jego nowy cel jest blisko, może utknąć.
            new_area_obj = Area(
                detected_position_world[0], detected_position_world[1], detected_position_world[2],
                field_parameters_from_scan.get('humidity', 50),
                field_parameters_from_scan.get('pH', 7.0),
                field_parameters_from_scan.get('microbiome', "Unknown"),
                field_parameters_from_scan.get('temperature', 20.0),
                field_parameters_from_scan.get('mineral_composition', "Unknown"),
                name=discovered_field_name,       
                handle=-1,                        
                last_visited_time=time.time()     
            )
            self.fields[discovered_field_name] = new_area_obj
            
            # Dodaj jako przeszkodę
            self.obstacle_list.append({'x': new_area_obj.x, 'y': new_area_obj.y, 'radius': FIELD_RADIUS_FOR_OBSTACLES, 'type': 'field', 'id': discovered_field_name})
            print(f"[Centrala] Dodano nowe pole {discovered_field_name} do rejestru i listy przeszkód.")

            # Można by stworzyć obiekt w symulacji dla tego nowego pola, jeśli to potrzebne
            # np. sim.createPrimitiveShape(...) i sim.writeCustomDataBlock(...)
            # To zależy, czy odkryte pola mają być wizualizowane/interaktywne tak samo jak te początkowe.

    def stop(self):
        print("[Centrala] Zatrzymywanie...")
        self.running = False
        if self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=5) # Daj wątkowi czas na zakończenie
        print("[Centrala] Zatrzymana.")