import pygame
import threading
import time
import os
from sound_environment import SoundEnvironment

class SoundController:
    def __init__(self):
        """Inizializzazione del controller audio"""
        # Inizializza pygame per la gestione audio
        pygame.mixer.init()
        self.sound_env = SoundEnvironment()
        
        # Parametri di controllo
        self.master_volume = 0.5  # Volume generale (0.0 - 1.0)
        self.sounds = {}  # Dizionario di suoni attivi {channel: {'sound': sound_obj, 'volume': float, 'filename': str}}
        self.is_paused = False  # Stato di pausa globale
        self.current_location = None  # Location corrente
        self.location_lock = threading.Lock()  # Per thread safety
        
        # Monitoraggio dei canali
        self.monitor_thread = None
        self.running = False
        
    def start(self):
        """Avvia il controller e il monitoraggio"""
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_channels, daemon=True)
            self.monitor_thread.start()
            
    def stop(self):
        """Ferma il controller e tutti i suoni"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            
        # Ferma tutti i suoni
        pygame.mixer.stop()
        self.sounds.clear()
        
    def set_location_sounds(self, location_category):
        """Imposta i suoni per la location specificata"""
        with self.location_lock:
            if location_category == self.current_location:
                return  # Stessa location, nessuna modifica necessaria
                
            # Ferma tutti i suoni attuali
            self.stop_all_sounds()
            
            # Ottieni nuovi suoni per la categoria
            sound_files = self.sound_env.get_sounds_for_location(location_category, max_sounds=3)
            
            # Se non ci sono suoni per questa categoria, prova con "natura" come fallback
            if not sound_files and location_category != "natura":
                sound_files = self.sound_env.get_sounds_for_location("natura", max_sounds=2)
            
            self.current_location = location_category
            
            # Avvia i nuovi suoni
            for sound_file in sound_files:
                if os.path.exists(sound_file):
                    self.play_sound(sound_file)
                    
    def play_sound(self, sound_file, loop=True, volume=None):
        """Riproduce un file audio"""
        try:
            if volume is None:
                volume = self.master_volume
                
            # Cerca un canale libero
            channel = None
            for i in range(pygame.mixer.get_num_channels()):
                if i not in self.sounds or not pygame.mixer.Channel(i).get_busy():
                    channel = i
                    break
                    
            # Se non ci sono canali liberi, ne crea uno nuovo
            if channel is None:
                channel = pygame.mixer.find_channel()
                if not channel:
                    pygame.mixer.set_num_channels(pygame.mixer.get_num_channels() + 1)
                    channel = pygame.mixer.Channel(pygame.mixer.get_num_channels() - 1)
                    
            # Carica e riproduce il suono
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(volume * self.master_volume)
            
            channel_obj = pygame.mixer.Channel(channel)
            loops = -1 if loop else 0  # -1 = loop infinito
            channel_obj.play(sound, loops=loops)
            
            # Registra il suono attivo
            self.sounds[channel] = {
                'sound': sound,
                'volume': volume,
                'filename': sound_file,
                'channel': channel_obj
            }
            
            return channel
        except Exception as e:
            print(f"Errore nella riproduzione del suono {sound_file}: {e}")
            return None
            
    def stop_sound(self, channel):
        """Ferma un suono specifico"""
        if channel in self.sounds:
            self.sounds[channel]['channel'].stop()
            del self.sounds[channel]
            
    def stop_all_sounds(self):
        """Ferma tutti i suoni attivi"""
        for channel in list(self.sounds.keys()):
            self.stop_sound(channel)
            
    def pause_all(self):
        """Mette in pausa tutti i suoni"""
        if not self.is_paused:
            for sound_info in self.sounds.values():
                if sound_info['channel'].get_busy():
                    sound_info['channel'].pause()
            self.is_paused = True
            
    def resume_all(self):
        """Riprende la riproduzione di tutti i suoni in pausa"""
        if self.is_paused:
            for sound_info in self.sounds.values():
                sound_info['channel'].unpause()
            self.is_paused = False
            
    def set_master_volume(self, value):
        """Imposta il volume principale (0.0 - 1.0)"""
        self.master_volume = max(0.0, min(1.0, value))
        # Aggiorna il volume di tutti i suoni
        for sound_info in self.sounds.values():
            sound_info['sound'].set_volume(sound_info['volume'] * self.master_volume)
            
    def set_sound_volume(self, channel, volume):
        """Imposta il volume di un suono specifico"""
        if channel in self.sounds:
            volume = max(0.0, min(1.0, volume))
            self.sounds[channel]['volume'] = volume
            self.sounds[channel]['sound'].set_volume(volume * self.master_volume)
            
    def get_active_sounds(self):
        """Restituisce informazioni sui suoni attualmente in riproduzione"""
        active_sounds = []
        for channel, sound_info in self.sounds.items():
            if sound_info['channel'].get_busy() or self.is_paused:
                active_sounds.append({
                    'channel': channel,
                    'filename': os.path.basename(sound_info['filename']),
                    'volume': sound_info['volume'],
                    'is_playing': sound_info['channel'].get_busy()
                })
        return active_sounds
        
    def _monitor_channels(self):
        """Thread per monitorare i canali e gestire i loop"""
        while self.running:
            # Controlla i canali inattivi
            for channel in list(self.sounds.keys()):
                if not self.sounds[channel]['channel'].get_busy() and not self.is_paused:
                    # Il suono è finito, rimuovilo dalla lista
                    del self.sounds[channel]
            time.sleep(0.5)  # Controlla ogni mezzo secondo
            
    def cleanup(self):
        """Pulizia delle risorse"""
        self.stop()
        pygame.mixer.quit()