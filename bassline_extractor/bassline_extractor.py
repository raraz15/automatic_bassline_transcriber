#!/usr/bin/env python
# coding: utf-8

import os
import sys
import time
import traceback

import numpy as np
from tqdm import tqdm

from demucs.pretrained import load_pretrained

from utilities import get_directories, init_folders, read_metadata
from .extractor_classes import BasslineExtractor, SimpleExtractor

project_dir = '/scratch/users/udemir15/ELEC491/bassline_transcription'
#project_dir = '/mnt/d/projects/bassline_extraction'


def extract_single_bassline(title, directories, track_dicts, date, separator=None, fs=44100, N_bars=4):
    """
    Creates a Bassline_Extractor object for a track using the metadata provided. Extracts and Exports the Bassline.
    """

    try:

        extractor = BasslineExtractor(title, directories, track_dicts, separator, fs, N_bars)

        # Estimate the Beat Positions and Export
        beat_positions = extractor.beat_detector.estimate_beat_positions(extractor.track.track)
        extractor.beat_detector.export_beat_positions() 


        # Estimate the Chorus Position and Extract
        extractor.chorus_detector.estimate_chorus(beat_positions, epsilon=2)         
        extractor.chorus_detector.export_chorus_start_beat_idx()            
        extractor.chorus_detector.export_chorus_beat_positions()

        # Extract the Chorus and Export 
        chorus = extractor.chorus_detector.extract_chorus()
        extractor.chorus_detector.export_chorus()


        # Extract the Bassline from the Chorus 
        #extractor.source_separator.separate_bassline(chorus)   
        #extractor.source_separator.process_bassline()

        # Export the bassline
        #extractor.source_separator.export_bassline()           

    except KeyboardInterrupt:
        import sys
        sys.exit()
        pass
    except KeyError as key_ex:
        print('Key Error on: {}'.format(title))
        exception_logger(directories, key_ex, date, title, 'KeyError')
    except FileNotFoundError as file_ex:
        print('FileNotFoundError on: {}'.format(title))
        exception_logger(directories, file_ex, date, title, 'FileNotFoundError')
    except RuntimeError as runtime_ex:
        print('RuntimeError on: {}'.format(title))
        exception_logger(directories, runtime_ex, date, title, 'RuntimeError')
    except Exception as ex:     
        print("There was an unexpected error on: {}".format(title))
        exception_logger(directories, ex, date, title, 'unexpected') 

# TODO: infer text_id from ex
def exception_logger(directories, ex, date, title, text_id):
    exception_str = ''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__))
    with open(os.path.join(directories['extraction']['exceptions'], '{}_{}.txt'.format(date, text_id)), 'a') as outfile:
        outfile.write(title+'\n'+exception_str+'\n')
        outfile.write('--'*40+'\n')    

def main(directories_path=project_dir, track_dicts_name='TechHouse_track_dicts.json', idx=0):

    directories, track_dicts, track_titles, date = prepare(directories_path, track_dicts_name)

    separator = load_pretrained('demucs_extra')

    start_time = time.time()
    for title in tqdm(track_titles[idx:]):

        print('\n'+title)
        extract_single_bassline(title, directories, track_dicts, date, separator, fs=44100)

        with open('Completed_{}_{}.txt'.format(date, track_dicts_name.split('.json')[0]), 'a') as outfile:
            outfile.write(title+'\n')

    print('Total Run:', time.strftime("%H:%M:%S",time.gmtime(time.time() - start_time)))


def prepare(directories_path, track_dicts_name='TechHouse_track_dicts.json'):

    date = time.strftime("%Y-%m-%d_%H-%M-%S")

    directories = get_directories(directories_path)

    init_folders(directories['extraction'])
            
    _, track_dicts, track_titles = read_metadata(directories, track_dicts_name)

    return directories, track_dicts, track_titles, date


def separate_from_chorus(directories_path=project_dir):

    directories, track_dicts, track_titles, date = prepare(directories_path)

    separator = load_pretrained('demucs_extra')

    start_time = time.time()
    for title in tqdm(track_titles):

        print('\n'+title)

        extractor = SimpleExtractor(title, directories, track_dicts, separator)
        
        extractor.extract_and_export_bassline()
        
    print('Total Run:', time.strftime("%H:%M:%S",time.gmtime(time.time() - start_time)))


if __name__ == '__main__':

    main()