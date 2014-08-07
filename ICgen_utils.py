# -*- coding: utf-8 -*-
"""
Created on Tue Aug  5 17:37:03 2014

@author: ibackus
"""
__version__ = "$Revision: 1 $"
# $Source$

import subprocess
import multiprocessing
import glob
import numpy as np
import isaac
import pynbody
SimArray = pynbody.array.SimArray
import os

def est_eps(f, changa_preset=None, verbose=True, logfile_name=None):
    """
    Estimates the gravitational softening length as 1/2 the mean SPH smoothing
    length.  Uses ChaNGa to calculate the smoothing length
    
    **ARGUMENTS**
    
    f : str -or- tipsy snapshot (see pynbody)
        IF a string, f is the filename of a .param file for running ChaNGa.
        IF a snapshot, a temporary file is saved for running ChaNGa
    changa_preset : string
        (optional) A configuration preset for running ChaNGa.  See changa_command
        for possible presets.  If None, the default preset is used
    verbose : bool
        (optional) If true, prints the ChaNGa output to stdout
    logfile_name : str
        (optional) If set, ChaNGa stdout is saved to logfile_name
        
    **RETURNS**
    
    eps : SimArray (1 number)
        Estimate of a reasonable gravitational softening length
    """
    if isinstance(f, str):
        
        param_name = f
        param = isaac.configparser(param_name)
        f_prefix = param['achOutName']
        
    else:
        
        # Filenames
        f_prefix = 'temp_snapshot'
        f_name = f_prefix + '.std'        
        param_name = f_prefix + '.param'
        # Save snapshot
        f.write(filename=f_name, fmt=pynbody.tipsy.TipsySnap)
        # Save param file
        param = isaac.make_param(f, filename=f_name)
        isaac.configsave(param, param_name)
        
    command = changa_command(param_name, changa_preset, changa_args='-n 0')
    p = changa_run(command, verbose=verbose, logfile_name=logfile_name, force_wait=True)
    
    # Load smoothing lengths
    h_name = f_prefix + '.000000.smoothlength'
    h = np.genfromtxt(h_name, skiprows=1, skip_footer=1)
    
    # Estimate gravitational softening as 1/2 the mean smoothing length
    eps = h.mean()/2
    
    # Cleanup
    for a in glob.glob(f_prefix + '.000000*'):
        
        os.remove(a)
    
    eps_units = param['dKpcUnit'] * pynbody.units.kpc
    
    return SimArray(eps, eps_units)
    

def changa_run(command, verbose = True, logfile_name=None, force_wait=False):
    """
    A wrapper for running ChaNGa
    
    **ARGUMENTS**
    
    command : str
        A full command line command for running ChaNGa.  Can be produced from 
        defaults using ICgen_utils.changa_command
    verbose : bool
        (optional) Flag for printing ChaNGa output to stdout.
        If True - stdout is printed.  This will effectively makes changa_run
        wait on ChaNGa completion
    logfile_name : str
        (optional) If set, saves ChaNGa output to file
    force_wait : bool
        (optional) Default = False
        If set, forces wait on ChaNGa before completion
    
    **RETURNS**
    
    p : subprocess.Popen
        A process object created by subprocess.Popen for the ChaNGa command
    """
    
    if logfile_name is not None:
        
        logfile = open(logfile_name, 'w')
        logfile.close()
        logfile = open(logfile_name, 'a')
    
    if verbose:
        
        output = subprocess.PIPE
        p = subprocess.Popen(command.split(), stderr=output, stdout=output)
        
        for line in iter(p.stdout.readline, ''):
            
            print line,
            if logfile_name is not None:
                
                logfile.write(line)
                
        p.wait()
        
    else:
        
        if logfile_name is not None:
            
            output = logfile
            
        else:
            
            output = subprocess.PIPE
            
        p = subprocess.Popen(command.split(), stderr=output, stdout=output)
        
    if force_wait:
        
        p.wait()
        
    return p

def changa_command(param_name, preset='local', changa_bin=None, changa_args='', runner_args=''):
    """
    A utility for created command line commands for running ChaNGa
    
    **ARGUMENTS**
    
    param_name : str
        Filename of the .param file used for ChaNGa
    preset : str
        if None, the default preset is used
        Default = 'local'
        Defaults to use.  Options are
            'none' (no arguments given)
            'local'
            'mpi'
    changa_bin : str
        Default = None
        Path to the ChaNGa binary to use.  If None, defaults are used
        Overrides preset binary
    changa_args : str
        Additional user supplied arguments for ChaNGa
    runner_args : str
        Additional user supplied arguments for the runner (ie charmrun or mpirun)
        
    **RETURNS**
    
    command : str
        A command line command for running ChaNGa
    """
    
    # ******************************
    # DEFAULT PRESET
    # ******************************
    if preset is None:
        
        preset = 'local'
        
    # ******************************
    # NONE PRESET
    # ******************************
    if preset == 'none':
        
        if changa_bin is None:
            # Location of the default changa binary
            changa_bin = os.popen('which ChaNGa').read().strip()
        
        command = '{} {} {} {}'.format(runner_args, changa_bin, \
        changa_args, param_name)
        command = ' '.join(command.split())
        
        return command
    
    # ******************************
    # LOCAL PRESET
    # ******************************
    elif preset == 'local':
        
        # Number of processes to use
        proc = multiprocessing.cpu_count() - 1
        
        # location of the ChaNGa binary
        if changa_bin is None:
            
            changa_bin = os.popen('which ChaNGa_sinks').read().strip()
        
        if proc < 1:
            
            proc = 1
            
        default_runner_args = '+p {} ++local'.format(proc)
        default_changa_args = '-D 3 +consph'
        runner = 'charmrun_sinks'
        
    # ******************************
    # MPI PRESET
    # ******************************
    elif preset == 'mpi':
        
        if changa_bin is None:
            
            changa_bin = os.popen('which ChaNGa_uw_mpi').read().strip()
        
        default_runner_args = '--mca mtl mx --mca pml cm'
        default_changa_args = '-D 3 +consph'
        runner = 'mpirun'
        
    # ----------------------------------------------------------
    # Add user supplied arguments
    changa_args = ' '.join([default_changa_args, changa_args])
    runner_args = ' '.join([default_runner_args, runner_args])
    command = ' '.join([runner, runner_args, changa_bin, changa_args, param_name])
    command = ' '.join(command.split())    
        
    return command
            
            
            
def arg_cat(arg_list):
    """
    STILL ALPHA!!! 
    
    arg_str = arg_cat([args1, args2, ...])
    
    Concatenates a list of various command line arguments.  arg_list should
    be a list containing command line argument strings.
    
    Priority is given to later arguments.  So arg_list[2] overwrites arg_list[1]
    if they share any flags
    
    **EXAMPLES**
    
    args1 = '-n 20 +cd 13 ++b fire testit'
    args2 = '-n 20 +cd 300'
    print arg_cat([args1, args2])
    
        returns:
        +cd 300 -n 20 testit ++b fire
    """
    
    args_dict = {}
    
    # Loop through all sets of arguments
    for args in arg_list:
        
        # Split args if it's not already a list
        if isinstance((args), str):
            
            args = args.split()
            
        # Parse arguments
        counter = 0
        
        while counter < len(args):
            
            key = args[counter]
            
            if (key[0] == '-') or (key[0] == '+'):
                # We have a flag followed by its value
                val = args[counter+1]
                counter += 2
                
            else:
                # We just have an argument
                val = ''
                counter += 1
                
            args_dict[key] = val
                
    args_str = ''
    
    for key, val in args_dict.iteritems():
        
        if val == '':
            
            # Tack on to the end
            args_str = ' '.join([args_str, key])
            
        else:
            
            # Place at beginning
            args_str = ' '.join([key, val, args_str])
            
    args_str = ' '.join(args_str.split())
    
    return args_str