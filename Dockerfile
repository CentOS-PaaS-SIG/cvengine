FROM fedora:27
MAINTAINER "Alex Corvin" <acorvin@redhat.com>

RUN yum -y install git python2-setuptools \
    sshpass libffi-devel gcc python-devel \
    openssl-devel make nss_wrapper redhat-rpm-config \
    libffi ansible standard-test-roles wget file \
    findutils && yum clean all

RUN pip install --upgrade pip && pip install --upgrade setuptools

COPY . /cvengine
RUN cd /cvengine && pip install -r requirements.txt \
    && python setup.py install

# Ensure that the root group has write access in $HOME
# This is necessary because, when running a container in
# Openshift, a random UID will be assigned at runtime. This
# UID will not have a valid username, but will be a member
# of the root group
RUN chgrp -Rf root $HOME && chmod -Rf g+w $HOME

COPY ci/standard-inventory-qcow2 /usr/share/ansible/inventory/standard-inventory-qcow2
ENV ANSIBLE_INVENTORY=/usr/share/ansible/inventory/standard-inventory-qcow2

ENTRYPOINT ["bash"]
CMD ["/cvengine/run_container_validation"]
