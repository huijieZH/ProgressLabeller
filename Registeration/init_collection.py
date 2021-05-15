import bpy

def register():
    ## clear all collection
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
    for obj in bpy.data.objects:	
        bpy.data.objects.remove(obj, do_unlink=True)
    ## -Model
    ## -Reconstruction
    ##   -pointcloud
    ##   -camera
    ##   -image
    model_collection = bpy.data.collections.new("Model")
    bpy.context.scene.collection.children.link(model_collection)
    ## reconstruction collection  
    reconstruction_collection = bpy.data.collections.new("Reconstruction")
    bpy.context.scene.collection.children.link(reconstruction_collection)
    ## camera collection  
    camera_collection = bpy.data.collections.new("Camera")
    reconstruction_collection.children.link(camera_collection)
    ## pointcloud collection  
    pointcloud_collection = bpy.data.collections.new("PointCloud")
    reconstruction_collection.children.link(pointcloud_collection)
    ## image collection  
    image_collection = bpy.data.collections.new("Image")
    reconstruction_collection.children.link(image_collection)

def unregister():
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection)
