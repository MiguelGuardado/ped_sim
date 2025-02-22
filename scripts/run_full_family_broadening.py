import networkx as nx
import subprocess
import argparse
import os
import sys
import numpy as np
import pandas as pd
import time
from run_single_family_broadening import *
from networkx.relabel import convert_node_labels_to_integers
from networkx.algorithms.operators.binary import disjoint_union
from networkx.algorithms.traversal.depth_first_search import dfs_predecessors

"""
run_full_family_broadening.py takes in a main family or simulates a main family. 
run_full_family_broadening.py iterates through each non-root founder and simulates a family with similar generations onto them.
if a main family is given, the root founder generation needs to be ommited in the -y flag
"""
#ex: python run_ped_sim.py -t run_full_family_broadening -c ipumps_sibship_dist.txt -y 1850 1860 1870
# python run_full_family_broadening.py -c ipumps_sibship_dist.txt -y 1850 1860 1870

# record start time
start = time.time()

def load_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--years_to_sample', nargs='+', type=int)
    parser.add_argument('-c', '--census_filepath', type=str)
    parser.add_argument('-o', '--output_prefix', type=str, default = 'joint_family_output')
    parser.add_argument('-mo', '--main_family_output_prefix', type=str, default = 'main_family')
    parser.add_argument('-mf', '--main_family')
    return parser.parse_args()

def fam_check_gen(family):
    '''
    check the family profile and returns the number of generations
    '''

    #list all indiv generations 
    fam = pd.read_csv(f'{family}', sep='\t')
    df = pd.DataFrame(fam)
    # gen = df.Gen.unique()

    return len(df['Gen'].unique()) - 1
    # return(len(gen)-1)

if __name__ == '__main__':
    #load in user arguments
    user_args = load_args()

    if user_args.output_prefix == None or user_args.output_prefix == 'None':
        user_args.output_prefix = 'joint_family_output'


    u_years = user_args.years_to_sample
    u_census = user_args.census_filepath
    u_main_family = user_args.main_family
    u_output = user_args.output_prefix
    u_mo = user_args.main_family_output_prefix


    #sets up years to run as a terminal command
    years_str = f'-y'
    for i in u_years:
        years_str += f' {i}'

    #initialize count for file names of joint families
    count = 1
    main_family_filepath = ''
    #create or load in main family
    if user_args.main_family == None or user_args.main_family == 'None':# read in user imput family
        num_gen = 0
        while num_gen < len(u_years): #makes sure the simulated main family has the same number of generations as the user imputed generatrions. if less, the main family will be simulated again
            sim_ped_cmd = f'python scripts/sim_pedigree_v2.py {years_str} -c {u_census} -o {u_mo}' 
            subprocess.run(sim_ped_cmd, shell=True)
            main_family = nx.read_edgelist(f'{u_mo}.nx', create_using = nx.DiGraph())
            print('main family created')
            num_gen = fam_check_gen(f'{u_mo}_profiles.txt')
            main_family_filepath = u_mo

        num_gen = fam_check_gen(f'{u_mo}_profiles.txt')
        count = count + 1
    else: # read in user imput family
        #if user imputs main family, the user must have a profiles file ex. main_family_profiles.txt
        main_family = nx.read_edgelist(u_main_family, create_using = nx.DiGraph())
        main_family_filepath = u_main_family
        # checks if the generation years match the users main family
        if len(main_family) < len(u_years):
            print('Number of generations in submitted family (-mf) does not match number of generations requested (-y)')
            exit()

    #find founders in main family
    founders = find_founders(main_family)
    founders = founders[2:] # asssumes root founders are first 2 founders and removes them from founder list
    print("Founders to extend breadth uppon: ", founders)

    #kill counter to avoid inf loop
    kill = 0
    #initialize joint family
    sim_ped_cmd = f'python scripts/sim_pedigree.py {years_str} -c {u_census} -o {u_output}_fam0' # -s {input_seed}'
    subprocess.run(sim_ped_cmd, shell=True, capture_output=True)
    join_cmd = f'python scripts/run_single_family_broadening.py -n1 {main_family_filepath}.nx -n2 {u_output}_fam0.nx -pr1 {main_family_filepath}_profiles.txt -pr2 {u_output}_fam0_profiles.txt -o {u_output} -cf {founders[0]}'
    
    # records errorcode in case family_broadening fails to connect main family and joint family. if an error occurs, new family is created 
    errorcode = subprocess.run(join_cmd, shell=True, capture_output=True)
    subprocess.run(join_cmd, shell=True, capture_output=True)

    # checks if the siumulated family is compatible with the main family. if not run again
    while errorcode.returncode == 1:
        sim_ped_cmd = f'python scripts/sim_pedigree.py {years_str} -c {u_census} -o {u_output}_fam0' # -s {input_seed}'
        subprocess.run(sim_ped_cmd, shell=True, capture_output=True)
        if user_args.main_family:
            mf = u_main_family.replace('.nx','')
            join_cmd = f'python scripts/run_single_family_broadening.py -cf {founders[0]} -n1 {mf}.nx -n2 {u_output}_fam0.nx -pr1 {mf}_profiles.txt -pr2 {u_output}_fam0_profiles.txt -o {u_output}'
        else:
            join_cmd = f'python scripts/run_single_family_broadening.py  -cf {founders[0]} -n1 {main_family_filepath}.nx -n2 {u_output}_fam0.nx -pr1 {main_family_filepath}_profiles.txt -pr2 {u_output}_fam0_profiles.txt -o {u_output}'
            
        errorcode = subprocess.run(join_cmd, shell=True, capture_output=True)

        # suppose to prevent an infinite loop
        kill = kill + 1
        if kill == 10:
            python = sys.executable
            os.execl(python, python, *sys.argv)

    # loops throught the remaining founders, simulates families then attaches to main family
    # we do this so that we can mainting the origional main family
    count=1
    for i in founders[1:]:
        # create family to join main family
        sim_ped_cmd = f'python scripts/sim_pedigree.py {years_str} -c {u_census} -o {u_output}_fam{count}'
        subprocess.run(sim_ped_cmd, shell=True)
        join_cmd = f'python scripts/run_single_family_broadening.py -n1 {u_output}.nx -n2 {u_output}_fam{count}.nx -pr1 {u_output}_profiles.txt -pr2 {u_output}_fam{count}_profiles.txt -o {u_output} -cf {i}'
        errorcode = subprocess.run(join_cmd, shell=True, capture_output=True)
        while errorcode.returncode == 1:
            sim_ped_cmd = f'python scripts/sim_pedigree.py {years_str} -c {u_census} -o {u_output}_fam{count}' # -s {input_seed}'
            subprocess.run(sim_ped_cmd, shell=True, capture_output=True)
            join_cmd = f'python scripts/run_single_family_broadening.py -n1 {u_output}.nx -n2 {u_output}_fam{count}.nx -pr1 {u_output}_profiles.txt -pr2 {u_output}_fam{count}_profiles.txt -o {u_output} -cf {i}'
            errorcode = subprocess.run(join_cmd, shell=True, capture_output=True)
            print('creating new fam')
    
        print(f'connection successful for fam{count} at founder', i)
        
        # remove simulated family after joining
        os.remove(f"{u_output}_fam{count}.nx")
        os.remove(f"{u_output}_fam{count}_profiles.txt")

        #increase count for file name
        count += 1

    # remove initial joint family
    os.remove(f"{u_output}_fam0.nx")
    os.remove(f"{u_output}_fam0_profiles.txt")
    os.remove(f"relabled_fam.nx")