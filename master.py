import boto.ec2
from sigopt import Connection
from optimization import optimize
import execnet
import time
import threading
import os
import argparse

# Creates specified number of instances of specified type and adds "Test_assignment" tag.
def create_instances(num_workers=3, type_of_machine='m3.medium'):
    # Create AWS connection.
    aws_conn = boto.ec2.connect_to_region("us-west-1")
 
    reservation = aws_conn.run_instances(
        'ami-48db9d28',
        min_count=num_workers,
        max_count=num_workers,
        key_name='valerie',
        instance_type=type_of_machine,
        security_groups=['default', 'default-ssh'])

    # Tag created instances 'Test_assignment'.
    instance_ids = [i.id for i in reservation.instances]
    tag_name = 'Test_assignment'
    aws_conn.create_tags(instance_ids, {tag_name: ''})
    if reservation:
        print "Instances were created successfully"
    
# Runs on threads to get new suggestions while not blocking processing of elements in the queue.
def get_suggestion(experiment_id, channel, sigopt_conn):
    suggestion = sigopt_conn.experiments(experiment_id).suggestions().create()
    channel.send((suggestion.id, suggestion.assignments['x'], suggestion.assignments['y']))

def log(verbose, message):
    if verbose:
        print message

# Runs optimization loop on specified number of observations
# using channels to run optimization using suggestions concurrently on created instances.
def master(sigopt_token, path_to_key, verbose, n_observations=30):
    aws_conn = boto.ec2.connect_to_region("us-west-1")
    instances = aws_conn.get_only_instances(filters={'tag:Test_assignment':''})
    # Creating a list of channels - one for every instance. It can be increased to match number of CPUs on every machine.
    channels = []
    for i in instances:
        if i.state == 'running':
            dns = i.public_dns_name
            # Create gateway to execute code remotely via SSH.
            gt = execnet.makegateway(
                "ssh=-i %s -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null ubuntu@%s" % 
                (path_to_key, dns))
            # If the machine is multicore the number of channels can be adjusted up to 1 channel per core for every machine using for loop.
            # for i in range(4):  # 4 CPUs
            channels.append(gt.remote_exec(optimize))
    # Create multichannel comprising all of the channels.
    mch = execnet.MultiChannel(channels)
    # Create queue for retrieving elements from channel with -1 appended on channel closing.
    queue = mch.make_receive_queue(endmarker=-1)

    # Create sigopt connection and experiment.
    sigopt_conn = Connection(client_token=sigopt_token or os.environ.get('SIGOPT_TOKEN'))
    experiment = sigopt_conn.experiments().create(
        name='Franke Optimization (Python)',
        parameters=[
            dict(name='x', type='double', bounds=dict(min=0.0, max=1.0)),
            dict(name='y', type='double', bounds=dict(min=0.0, max=1.0)),
        ],
    )
    # First suggestion to try.
    suggestion = sigopt_conn.experiments(experiment.id).suggestions().create()
    # Measure time elapsed during optimization running.
    time_before = time.time()
    terminated = 0
    while 1:
        # Get the next element and channel from which it was retrieved from queue.
        channel, item = queue.get()
        if item == -1:
            terminated += 1
            log(verbose, "terminated %s" % channel.gateway.id)
            # If terminated all the channels then finish the optimization process.
            if terminated == len(mch):
                log(verbose, "got all results, terminating")
                break
            continue
        # Send computed value for the optimize function to SigOpt API.
        if item != "ready":
            suggestion_id = item[0]
            value = item[1]
            sigopt_conn.experiments(experiment.id).observations().create(
                suggestion=suggestion_id,
                value=value)
            log(verbose, "other side %s returned %r" % (channel.gateway.id, item))
        # Get new suggestion for paramteters from SigOpt API using threads 
        # so that it runs concurrently while processing other values from the queue.
        if n_observations > 0:
            log(verbose, n_observations)
            n_observations -= 1
            threading.Thread(target=get_suggestion, 
                            args=(experiment.id, channel, sigopt_conn)).start()
            log(verbose, "sent suggestion to %s" % channel.gateway.id)
        # If we reached the desired number of observations then close all channels.
        elif n_observations == 0:
            log(verbose, "no tasks remain, sending termination request to all")
            mch.send_each(None)
            n_observations = -1

    time_after = time.time()
    log(verbose, "optimization took %s ms" % ((time_after - time_before) * 1000.0))
    # Terminate the instances.
    aws_conn.terminate_instances([i.id for i in instances])

    print ("Best function value: %s. Parameters value corresponding to this function value: %s" % 
        (sigopt_conn.experiments(experiment.id).fetch().progress.best_observation.value, 
        sigopt_conn.experiments(experiment.id).fetch().progress.best_observation.assignments))

parser = argparse.ArgumentParser()
parser.add_argument("--create_instances", 
    help="Use this if you want to create instances. Omit if the instances are running and you want to evaluate the model on them.",
    action="store_true")
parser.add_argument("--num_machines", 
    help="Enter the number of instances to create. Default is 3.", type=int)
parser.add_argument("--machine_type", 
    help="Enter the type of machines to be created. Default is m3.medium.")
parser.add_argument("--sigopt_token", 
    help="Credentials token for SigOpt API (if not using environmental variable SIGOPT_TOKEN).")
parser.add_argument("--num_observations", 
    help="Enter the number of observations to evaluate the model on. Default is 30.", type=int)
parser.add_argument("--key_pair", 
    help="Enter the name of key pair without .pem extention.")
parser.add_argument("--path_to_private_key", 
    help="Enter absolute path to your private key. For example, /Users/Michael/.ssh/my_key.pem")
parser.add_argument("--v", 
    help="Print logging information.", action="store_true")
args = parser.parse_args()
if args.create_instances:
    if not args.key_pair:
        print "Key pair name must be provided for creating instances."
    else:
        create_instances(num_workers=args.num_machines or 3, type_of_machine=args.machine_type or 'm3.medium')
else:
    if not (args.sigopt_token or os.environ.get('SIGOPT_TOKEN')):
        print "Sigopt credentials must be either set in SIGOPT_TOKEN environment variable or provided with --sigopt_token option."
    elif not args.path_to_private_key:
        print "Absolute path to your private key must be provided to create ssh connections to the instances."
    else:
        master(sigopt_token=args.sigopt_token or os.environ.get('SIGOPT_TOKEN'), path_to_key=args.path_to_private_key,
                n_observations=args.num_observations or 30, verbose=args.v)

