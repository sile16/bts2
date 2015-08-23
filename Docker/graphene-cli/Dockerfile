FROM debian:jessie

#Make the /root a volume so graphene data is outside the container and preserved between runs.
#VOLUME /cli_wallet_data_dir
ADD cli_wallet /
ENTRYPOINT ["/cli_wallet"]

