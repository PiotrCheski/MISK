class Area:
    def __init__(self, x, y, z, humidity, pH, microbiome, temperature, mineral_composition):
        self.x = x
        self.y = y
        self.z = z
        self.humidity = humidity
        self.pH = pH
        self.microbiome = microbiome
        self.temperature = temperature
        self.mineral_composition = mineral_composition

    def __str__(self):
        return (f"Area ({self.x}, {self.y}, {self.z})\n"
                f"Humidity: {self.humidity}%\n"
                f"pH: {self.pH}\n"
                f"Microbiome: {self.microbiome}\n"
                f"Temperature: {self.temperature}°C\n"
                f"Mineral Composition: {self.mineral_composition}")