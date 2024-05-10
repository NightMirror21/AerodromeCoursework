import tkinter as tk
from tkinter import ttk
import threading
import time
import random

class AerodromeInterface:
    def __init__(self, aerodrome):
        self._aerodrome = aerodrome
        self._root = tk.Tk()
        self._root.title("Аэродром")
        self._root.resizable(False, False)
        self._root.attributes("-fullscreen", True)

        self._runway_frames = []
        self._log_text = tk.Text(self._root, wrap="word", height=20, width=50)
        self._log_text.grid(row=0, column=self._aerodrome.get_runway_count(), padx=10, pady=10, rowspan=2*self._aerodrome.get_runway_count(), sticky="nsew")

        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_rowconfigure(1, weight=0)

        for i in range(self._aerodrome.get_runway_count()):
            runway_frame = ttk.Frame(self._root)
            runway_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self._runway_frames.append(runway_frame)

        self._update_display()

        add_aircraft_frame = ttk.Frame(self._root)
        add_aircraft_frame.grid(row=1, column=0, columnspan=self._aerodrome.get_runway_count(), padx=10, pady=10, sticky="ew")
        
        ttk.Label(add_aircraft_frame, text="Позывной:").grid(row=0, column=0, padx=5, pady=5)
        self._callsign_entry = ttk.Entry(add_aircraft_frame)
        self._callsign_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_aircraft_frame, text="Требуемое время на посадку:").grid(row=0, column=2, padx=5, pady=5)
        self._landing_time_entry = ttk.Entry(add_aircraft_frame)
        self._landing_time_entry.grid(row=0, column=3, padx=5, pady=5)

        self._emergency_var = tk.BooleanVar()
        ttk.Checkbutton(add_aircraft_frame, text="Экстренная", variable=self._emergency_var).grid(row=0, column=4, padx=5, pady=5)

        add_button = ttk.Button(add_aircraft_frame, text="Добавить", command=self._add_aircraft)
        add_button.grid(row=0, column=5, padx=5, pady=5)

        random_button = ttk.Button(add_aircraft_frame, text="Заполнить случайно", command=self._fill_random_data)
        random_button.grid(row=0, column=6, padx=5, pady=5)

        close_button_frame = ttk.Frame(self._root)
        close_button_frame.grid(row=1, column=self._aerodrome.get_runway_count(), padx=10, pady=10, sticky="se")

        close_button = ttk.Button(close_button_frame, text="Закрыть", command=self._root.quit)
        close_button.grid(row=0, column=0, padx=5, pady=5)

        self._update_timer()

        self._root.mainloop()

    def _add_aircraft(self):
        callsign = self._callsign_entry.get()
        landing_time = int(self._landing_time_entry.get())
        emergency = self._emergency_var.get()
        aircraft = Aircraft(callsign, landing_time, emergency)
        self._aerodrome.add(aircraft)
        self._update_display()
        self._log_action(f"Самолёт {callsign} добавлен.")

    def _send_for_second_round(self, aircraft):
        success = self._aerodrome.send_for_second_round(aircraft)
        if success:
            self._update_display()
            self._log_action(f"Самолёт {aircraft.get_id()} отправлен на второй круг.")

    def _send_to_another_runway(self, aircraft):
        self._aerodrome.send_to_another_runway(aircraft)
        self._update_display()
        self._log_action(f"Самолёт {aircraft.get_id()} перемещён на другую полосу.")

    def _log_action(self, action):
        self._log_text.insert(tk.END, action + "\n")
        self._log_text.see(tk.END)

    def _update_display(self):
        for i, runway in enumerate(self._aerodrome.runways):
            for widget in self._runway_frames[i].winfo_children():
                widget.destroy()

            ttk.Label(self._runway_frames[i], text=f"Полоса {i+1}").grid(row=0, columnspan=4)

            for j, aircraft in enumerate(runway.get_queue()):
                emergency_text = "(экстренно)" if aircraft.is_emergency_landing_required() else ""
                ttk.Label(self._runway_frames[i], text=f"{aircraft.get_id()}").grid(row=j+1, column=0)
                ttk.Label(self._runway_frames[i], text=f"~{aircraft.get_remaining_flight_time()}").grid(row=j+1, column=1)
                ttk.Label(self._runway_frames[i], text=emergency_text).grid(row=j+1, column=2)
                if j < len(runway.get_queue()) - 1:
                    ttk.Button(self._runway_frames[i], text="На второй круг", command=lambda ac=aircraft: self._send_for_second_round(ac)).grid(row=j+1, column=3)
                ttk.Button(self._runway_frames[i], text="На другую полосу", command=lambda ac=aircraft: self._send_to_another_runway(ac)).grid(row=j+1, column=4)

    def _fill_random_data(self):
        call_signs = ["Ан-2", "Ил-14", "Ту-104", "Ил-18", "Ан-24", "Ту-134", "Ил-62", "Як-40", "Ту-144", "Ил-86"]
        emergency = random.choice([True, False])
        call_sign = random.choice(call_signs) + "-" + str(random.randint(10, 100))

        self._callsign_entry.delete(0, tk.END)
        self._callsign_entry.insert(0, call_sign)
        self._landing_time_entry.delete(0, tk.END)
        self._landing_time_entry.insert(0, random.randint(15, 60))
        self._emergency_var.set(emergency)

    def _update_timer(self):
        self._update_display()
        self._root.after(1000, self._update_timer)


class Aerodrome:
    def __init__(self):
        self.runways = [Runway(), Runway()]
        timer_thread = threading.Thread(target=self._check_landing, daemon=True)
        timer_thread.start()

    def get_runway_count(self):
        return len(self.runways)
    
    def add(self, aircraft):
        min_landing_time = float('inf')
        min_runway_index = -1
        for runway_index, runway in enumerate(self.runways):
            if runway.get_landing_time() < min_landing_time:
                min_landing_time = runway.get_landing_time()
                min_runway_index = runway_index
        self.runways[min_runway_index].add_aircraft(aircraft)
            
    def send_for_second_round(self, aircraft):
        for runway in self.runways:
            if runway.contains_plane(aircraft.get_id()):
                runway.send_around(aircraft.get_id())
                return True
        return False

    def send_to_another_runway(self, aircraft):
        for runway in self.runways:
            if runway.contains_plane(aircraft.get_id()):
                from_runway_index = self.runways.index(runway)
                to_runway_index = (from_runway_index + 1) % len(self.runways)
                self._transfer_aircraft(aircraft, from_runway_index, to_runway_index)
                break

    def _transfer_aircraft(self, aircraft, from_runway_index, to_runway_index):
        for runway in self.runways:
            if runway.contains_plane(aircraft.get_id()):
                runway.remove_aircraft(aircraft.get_id())
                self.runways[to_runway_index].add_aircraft(aircraft)
                break

    def _check_landing(self):
        while True:
            time.sleep(1)
            for runway in self.runways:
                runway.check_landing()

class Runway:
    def __init__(self):
        self._aircraft_queue = []
        
    def get_queue(self):
        return self._aircraft_queue

    def send_around(self, aircraft_id):
        for aircraft in self._aircraft_queue:
            if aircraft.get_id() == aircraft_id:
                self.remove_aircraft(aircraft_id)
                self.add_aircraft(aircraft)
                return True
        return False

    def contains_plane(self, aircraft_id):
        return any(aircraft.get_id() == aircraft_id for aircraft in self._aircraft_queue)

    def _recalculate_landing_times(self):
        total_landing_time = 0
        for aircraft in self._aircraft_queue:
            total_landing_time += aircraft.get_landing_time()
            aircraft._remaining_landing_time = total_landing_time

    def add_aircraft(self, aircraft):
            if aircraft.is_emergency_landing_required():
                self._aircraft_queue.insert(0, aircraft)
            else:
                self._aircraft_queue.append(aircraft)
            self._recalculate_landing_times()

    def get_landing_time(self):
        total_time = 0
        for aircraft in self._aircraft_queue:
            total_time += aircraft.get_landing_time()
        return total_time

    def remove_aircraft(self, aircraft_id):
        for aircraft in self._aircraft_queue:
            if aircraft.get_id() == aircraft_id:
                self._aircraft_queue.remove(aircraft)
                self._recalculate_landing_times()
                return

    def check_landing(self):
        landed_planes = []
        for aircraft in self._aircraft_queue:
            aircraft.reduce_landing_time(1)
            if aircraft.get_remaining_flight_time() <= 0:
                landed_planes.append(aircraft.get_id())
        self._aircraft_queue = [aircraft for aircraft in self._aircraft_queue if aircraft.get_id() not in landed_planes]
        return landed_planes

class Aircraft:
    def __init__(self, callsign, landing_time, emergency=False):
        self._callsign = callsign
        self._initial_landing_time = landing_time
        self._remaining_landing_time = landing_time
        self._emergency = emergency

    def is_emergency_landing_required(self):
        return self._emergency

    def get_id(self):
        return self._callsign

    def get_landing_time(self):
        return self._initial_landing_time

    def reduce_landing_time(self, time):
        self._remaining_landing_time -= time

    def get_remaining_flight_time(self):
        return self._remaining_landing_time
    
if __name__ == "__main__":
    aerodrome = Aerodrome()
    aerodrome_interface = AerodromeInterface(aerodrome)
