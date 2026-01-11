# autoscale-automation   
change the subnets, vpcid, and all other factors in code    

    
python3 -m venv venv  
source venv/bin/activate  
pip install boto3


if you want to check credentials you can run:  
aws configure  

or edit the ~/.aws/credentials file and add secret, access, sessiontoken, and region there (maybe region in the other file)
