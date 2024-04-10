#!/bin/bash

replace_deployment_name() {
    sed "s/{{ DEPLOYMENT_NAME }}/$1/g" nginx-deployment.yaml > nginx-deployment-temp.yaml
}

for((i=1; i<=500; i++))
    do
        for ((i=1; i<=50; i++))
        do
            deployment_name="nginx-deployment-$i"
            replace_deployment_name $deployment_name
            kubectl create -f nginx-deployment-temp.yaml --namespace=default
            sleep 2
        done


        sleep 10


        for ((i=1; i<=50; i++))
        do
            deployment_name="nginx-deployment-$i"
            kubectl delete deployment $deployment_name --namespace=default 
        done

        echo "All deployments deleted."
        sleep 3
    done

rm -f nginx-deployment-temp.yaml