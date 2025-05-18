import time 

class Area:
    def __init__(self, x, y, z, humidity, pH, microbiome, temperature, mineral_composition,
                 name=None, handle=None, last_visited_time=None): # Dodane opcjonalne parametry
        self.x = x
        self.y = y
        self.z = z
        self.humidity = humidity
        self.pH = pH
        self.microbiome = microbiome
        self.temperature = temperature
        self.mineral_composition = mineral_composition

        # Atrybuty używane przez Centralę (lub inne moduły)
        self.name = name
        self.handle = handle # Handle obiektu w CoppeliaSim
        self.last_visited_time = last_visited_time if last_visited_time is not None else 0.0 # czas ostatniej wizyty
        self.target_params = {} # Słownik na docelowe parametry zadania (np. {'target_humidity': 70})

    def __str__(self):
        extra_info = ""
        if self.name:
            extra_info += f"Name: {self.name}\n"
        if self.handle is not None: # handle może być 0, więc sprawdzamy None
            extra_info += f"Handle: {self.handle}\n"
        if self.last_visited_time > 0:

            extra_info += f"Last Visited: {time.ctime(self.last_visited_time)}\n"
        
        return (f"Area ({self.x}, {self.y}, {self.z})\n"
                f"{extra_info}"
                f"Humidity: {self.humidity}%\n"
                f"pH: {self.pH}\n"
                f"Microbiome: {self.microbiome}\n"
                f"Temperature: {self.temperature}°C\n"
                f"Mineral Composition: {self.mineral_composition}")