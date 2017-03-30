SigOpt Take-Home Assignment
----------------------------------------------------

This is a program written as take-home assignment for SigOpt. It uses SigOpt API to find optimal parameters for the model in order to maximize it by getting suggestions for parameters from SigOpt, then evaluating the model on these parameters and sending the result back to SigOpt in the loop. Function evaluation runs remotely on AWS EC2 instances concurrently using execnet interface for gateway creation on each of the instances to execute code remotely on EC2 instances. The number of channels can be increased to match number of cores available on the EC2 instances. SigOpt API requests are made by master worker that runs on a local machine (but can be moved to one of the worker machines) in case we'll need to aggregate the results of function evaluation on different parameter values before sending to SigOpt. New suggestion requests are made in threads in order not to block further processing of returned values from the queue by latency introduced by network communication. I added 2 seconds delay to the optimization function to actually see that channels are running in parallel and measure improvement between different number of machines used to run the program. If you want to see how the program works without delay comment out *time.sleep(2)* in optimization.py.

Installation
----------------------------------------------------
To run this program you'll need python version 2.7 and the following libraries: execnet, sigopt, boto. To install them run the next commands in the terminal:
```
pip install execnet
pip install sigopt
pip install boto
```
Copy optimization.py file to the same directory as master.py file.
Your AWS credentials should be in the file ~/.boto that looks like this:
```
[Credentials]
aws_access_key_id = <your_access_key_here>
aws_secret_access_key = <your_secret_key_here>
```
In the AWS web console create security group named 'default-ssh' and add a rule allowing for inbound traffic from your IP via SSH.
Run
-----------------------------------------------------
In the terminal enter command 
```
python master.py --create_instances --key_pair <your_key_pair_name> --num_machines <number_of_instances> --machine_type <type_of_machines>
```
Arguments *num_machines* and *machine_type* are optional, the default values are 3 machines and 'm3.medium' type.
Example:
```
python master.py --create_instances --key_pair valerie --num_machines 5
```
You have to provide *key_pair* value in order to create instances.
When the instances are created you'll need to wait a couple of minutes before they are fully functional and we can ssh to them.
To optimize parameters for the function in optimization.py file type command 
```
python master.py --sigopt_token <your_sigopt_credentials> --num_observations <number_of_iterations> --path_to_private_key <absolute_path_to_private_key>
```
If you want to print logging information while the optimization loop is running add - -v argument. Argument *sigopt_token* is optional in case you use *export SIGOPT_TOKEN=<your_sigopt_credentials>* command. Argument *num_observations* is optional, default value is 30.
Example:
```
python master.py --path_to_private_key /Users/Michael/.ssh/my_key.pem --num_observations 50 --v
```
To read information on different flag usage run *python master.py --help* in the terminal.
Troubleshooting
----------------------------------------------------
If your number of running instances exceeds the number of opened suggestions in your SigOpt plan, you'll see error message in the terminal. This happens because evaluations are performed concurrently on all machines and in order to do it we're requesting the same amount of suggestions as the number of machines. 
When running "python master.py" command without --create_instances argument too soon you can see the error "Host not found". Just wait some more time before running the command again.
