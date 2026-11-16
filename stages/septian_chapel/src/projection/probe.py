import bpy
sc=bpy.context.scene
print("HAS_CNG", hasattr(sc,"compositing_node_group"))
ng=bpy.data.node_groups.new("C","CompositorNodeTree")
k=ng.nodes.new("CompositorNodeKuwahara")
print("KIN",[(i.name,i.type,getattr(i,'default_value',None) if not hasattr(getattr(i,'default_value',None),'__len__') else 'vec') for i in k.inputs])
print("KPROPS",[p.identifier for p in k.bl_rna.properties if not p.is_readonly][:40])
print("OUTS",[n for n in dir(bpy.types) if n.startswith("CompositorNodeOutput")])
fo=ng.nodes.new("CompositorNodeOutputFile")
print("FO",[p.identifier for p in fo.bl_rna.properties if not p.is_readonly][:40])
print("FOIN",[i.name for i in fo.inputs])
