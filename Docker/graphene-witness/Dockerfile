FROM debian:jessie

#Make the /root a volume so graphene data is outside the container and preserved between runs.
VOLUME /witness_node_data_dir
ADD witness_node /witness_node
ENTRYPOINT /witness_node
