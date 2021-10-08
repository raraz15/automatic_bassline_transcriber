#!/usr/bin/env python
# coding: utf-8

import os
import warnings

import numpy as np

from ..utilities import (get_chorus_beat_positions, get_quarter_beat_positions, get_track_scale,
                        read_scale_frequencies, export_function)
from ..MIDI_output import create_MIDI_file
from .transcription import (pYIN_F0, adaptive_voiced_region_quantization,
                            uniform_voiced_region_quantization, midi_sequence_to_midi_array,
                            extract_note_dicts, frequency_to_midi_sequence)

warnings.filterwarnings('ignore') 

OUTPUT_DIR = "data/outputs/"
F_MIN = 32.7
T_MAX = 1/F_MIN # Longesr Period

FS = 44100

FRAME_LEN = int(T_MAX*FS)

class BassLineTranscriber():

    #def __init__(self, bass_line_path, BPM, key, M=1, N_bars=4, frame_factor=8, silence_code=0):
    def __init__(self, bass_line_path, BPM, key, M=1, N_bars=4, hop_factor=64, silence_code=0):
        """
        BassLineTranscriber

            Params:
            -------
                bass_line_path (str): path to the bassline.npy
                BPM (float, str): BPM of the track
                key (str): scale, scale type of the track
                M (int 1,2,4,8): Downsampling rate to the pitch track
                N_bars (int, default=4): Number of bars to perform transcription on
                hop_factor (int, default=32): Number of F0 estimate samples that make up a beat
                silence_code (int, default=0): code integer to represent silent regions
        
        """

        self.title = os.path.splitext(os.path.basename(bass_line_path))[0]
        self.fs = FS

        self.key, self.scale_type = key.split(' ')      
        scale_frequencies = read_scale_frequencies()
        self.track_scale = get_track_scale(self.key, self.scale_type, scale_frequencies)

        self.M = [M] if isinstance(M, int) else M # decimation rates
        
        self.N_bars = N_bars
        self.BPM = float(BPM)        
        self.beat_duration = 60/self.BPM # in seconds

        F0_sample_length = int((self.beat_duration / hop_factor)*FS) # Number of audio samples an F0 sample corresponds to
        frame_factor = int(FRAME_LEN / F0_sample_length) # number of F0 samples that make an F0 estimation frame
        
        self.frame_factor = frame_factor # F0 estimation frame size w.r.t a beat

        print('frame length: {}'.format(FRAME_LEN))
        print('F0_sample_length: {}'.format(F0_sample_length))
        print('frame factor: {}'.format(frame_factor))


        # Output Directories
        self.output_dir = os.path.join(OUTPUT_DIR, self.title)
        self.F0_estimate_dir = os.path.join(self.output_dir, 'F0_estimate')
        self.pitch_track_dir = os.path.join(self.output_dir, 'pitch_track')
        self.quantized_pitch_track_dir = os.path.join(self.output_dir, "quantized_pitch_track")
        self.midi_dir = os.path.join(self.output_dir, 'midi')          
        
        chorus_beat_positions = get_chorus_beat_positions(self.output_dir)
        self.quarter_beat_positions = get_quarter_beat_positions(chorus_beat_positions)

        self.bass_line = np.load(bass_line_path)

        self.silence_code = silence_code

    def extract_pitch_track(self, pYIN_threshold=0.05):

        print('Starting the transcription process.')

        #Initial estimate | Confidence Filtered
        self.F0_estimate, self.pitch_track = pYIN_F0(self.bass_line,
                                                    beat_duration=self.beat_duration,
                                                    hop_factor=32,
                                                    N_bars=self.N_bars,
                                                    threshold=pYIN_threshold)                                                

    def quantize_pitch_track(self, filter_unk, epsilon, quantization_scheme):

        assert quantization_scheme in ['adaptive', 'uniform'], 'Choose between adaptive and uniform quantization!'

        if quantization_scheme == 'adaptive':
            self.pitch_track_quantized = adaptive_voiced_region_quantization(self.pitch_track,
                                                                self.track_scale,
                                                                self.quarter_beat_positions,
                                                                filter_unk, 
                                                                length_threshold=self.frame_factor,
                                                                epsilon=epsilon)
        else:
            self.pitch_track_quantized = uniform_voiced_region_quantization(self.pitch_track, self.track_scale, epsilon)

    def create_bass_line_MIDI_file(self):
        print('Creating the MIDI file.')
        midi_sequence = frequency_to_midi_sequence(self.pitch_track_quantized[1], self.silence_code)
        for m in self.M:
            # Downsample by m and convert to a MIDI file
            bass_line_midi_array = midi_sequence_to_midi_array(midi_sequence,
                                                                M=m,
                                                                N_qb=self.frame_factor,
                                                                silence_code=self.silence_code)                                                                                                                           
            midi_dir = os.path.join(self.midi_dir, str(m))
            os.makedirs(midi_dir, exist_ok=True)                                                                
            create_MIDI_file(bass_line_midi_array, self.BPM, self.title, midi_dir)        

    def export_F0_estimate(self):
        print('Exporting the F0 estimate.')
        export_function(self.F0_estimate, self.F0_estimate_dir, self.title)

    def export_pitch_track(self):
        export_function(self.pitch_track, self.pitch_track_dir, self.title)

    def export_quantized_pitch_track(self):
        export_function(self.pitch_track_quantized, self.quantized_pitch_track_dir, self.title)    

    def extract_notes(self):
        """ Finds the notes in and out the scale, mainly for plotting."""
        self.notes, self.unk_notes = extract_note_dicts(self.pitch_track_quantized, self.track_scale)