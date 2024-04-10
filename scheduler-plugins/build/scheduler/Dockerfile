# Copyright 2020 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
ARG ARCH
FROM golang:1.20

WORKDIR /go/src/sigs.k8s.io/scheduler-plugins
COPY . .
ARG ARCH
ARG RELEASE_VERSION
ENV USE_CUDA=0  
RUN RELEASE_VERSION=${RELEASE_VERSION}  USE_CUDA=${USE_CUDA} make build-scheduler.$ARCH

FROM $ARCH/debian:11
#FROM $ARCH/alpine:3.16

# Installazione delle dipendenze di Python
RUN apt update && \
    apt install --no-install-recommends -y python3 python3-pip build-essential linux-headers-amd64 libc6-dev
RUN python3 -m pip install --upgrade numpy setuptools
RUN python3 -m pip install Kubernetes
RUN python3 -m pip install torch torchvision torchaudio -f https://download.pytorch.org/whl/cpu/torch_stable.html
RUN python3 -m pip install matplotlib
RUN python3 -m pip install tensorboard

# Attivazione dell'ambiente virtuale già presente
ENV VIRTUAL_ENV=/etc/kubernetes/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY /.kube/config ~/.kube/config

# Script di attivazione
#RUN echo '#!/bin/sh' > /activateScript.sh && \
#    echo 'source /etc/kubernetes/venv/bin/activate' >> /activateScript.sh && \
#    echo 'echo "|-->[NetworkTraffic] Install kubernetes"' >> /activateScript.sh && \
#    echo '/etc/kubernetes/venv/bin/pip install kubernetes' >> /activateScript.sh && \
##    echo '/etc/kubernetes/venv/bin/python3 /etc/kubernetes/model/cleanrl/cleanrl/dqn.py --env-id Scheduling-v0' >> /activateScript.sh && \
#    echo '/etc/kubernetes/venv/bin/python3 /etc/kubernetes/model/main.py' >> /activateScript.sh && \
#    chmod +x /activateScript.sh

COPY --from=0 /go/src/sigs.k8s.io/scheduler-plugins/bin/kube-scheduler /bin/kube-scheduler

EXPOSE 8765

WORKDIR /bin
CMD ["kube-scheduler"]
# CMD unico che esegue lo script di attivazione e il kube-scheduler
#CMD ["/bin/sh", "-c", "/activateScript.sh && /bin/kube-scheduler"]
