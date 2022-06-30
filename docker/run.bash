XSOCK=/tmp/.X11-unix
XAUTH=/tmp/.docker.xauth
touch $XAUTH
xauth nlist $DISPLAY | sed -e 's/^..../ffff/' | xauth -f $XAUTH nmerge -

sudo docker run --gpus all -it -v $XSOCK:$XSOCK:rw -v $XAUTH:$XAUTH:rw --device=/dev/dri/card0:/dev/dri/card0 -e DISPLAY=$DISPLAY -e XAUTHORITY=$XAUTH blender blender
