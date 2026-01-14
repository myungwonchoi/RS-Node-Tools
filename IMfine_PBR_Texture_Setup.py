import c4d
import maxon
import os
import sys
import ctypes
from ctypes import wintypes

# 현재 파일의 디렉토리를 sys.path에 추가하여 utils 모듈을 임포트할 수 있게 함
sys.path.append(os.path.dirname(__file__))
from IMfine_Libs import IMfine_Utils

# --- Constants & IDs ---
ID_RS_NODESPACE = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")
ID_RS_STANDARD_MATERIAL = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.standardmaterial")
ID_RS_OUTPUT = maxon.Id("com.redshift3d.redshift4c4d.node.output")
ID_RS_TEXTURESAMPLER = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.texturesampler")
ID_RS_BUMPMAP = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.bumpmap")
ID_RS_DISPLACEMENT = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.displacement")

# Port IDs
PORT_RS_STD_BASE_COLOR = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color"
PORT_RS_STD_METALNESS = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.metalness"
PORT_RS_STD_ROUGHNESS = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refl_roughness"
PORT_RS_STD_OPACITY = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.opacity_color"
PORT_RS_STD_EMISSION = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.emission_color"
PORT_RS_STD_BUMP_INPUT = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.bump_input"

PORT_RS_TEX_PATH = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0" # This is the group, path is child
PORT_RS_TEX_OUTCOLOR = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor"

PORT_RS_BUMP_INPUT = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.input"
PORT_RS_BUMP_OUT = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.out"
PORT_RS_BUMP_TYPE = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.inputtype"

PORT_RS_DISP_TEXMAP = "com.redshift3d.redshift4c4d.nodes.core.displacement.texmap"
PORT_RS_DISP_OUT = "com.redshift3d.redshift4c4d.nodes.core.displacement.out"
PORT_RS_OUTPUT_DISPLACEMENT = "com.redshift3d.redshift4c4d.node.output.displacement"

# Colorspace
RS_INPUT_COLORSPACE_RAW = "RS_INPUT_COLORSPACE_RAW"

CHANNEL_SUFFIXES = {
    "diffuse_color": "BaseColor", # RS Material
    "base_color": "BaseColor", # Standard Material
    "normal": "Normal",
    "ao": "AO",
    "refl_metalness": "Metalic", # RS Material    
    "metalness": "Metalic", # Standard Material
    "refl_roughness": "Roughness",
    "refl_weight": "Specular",
    "glossiness": "Glossiness",
    "opacity_color": "Opacity",
    "translucency": "Translucency",
    "bump" : "Bump",
    "displacement" : "Displacement",
    "emission_color" : "Emissive"
}

def get_script_metadata():
    return {
        "name": "PBR Texture Setup",
        "description": "텍스처 파일들을 불러오며 머티리얼에 자동으로 연결합니다.",
        "tags": ["Redshift", "Material", "Texture"],
        "icon": "IMfine_PBR_Texture_Setup.tif"
    }

def ask_open_filenames(title="Select Files"):
    """
    Opens a native Windows file dialog for multi-file selection using ctypes.
    Returns a list of selected file paths.
    """
    # Constants
    OFN_ALLOWMULTISELECT = 0x00000200
    OFN_EXPLORER = 0x00080000
    OFN_FILEMUSTEXIST = 0x00001000
    
    # Structure definition
    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", wintypes.LPVOID),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", wintypes.LPVOID),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    # Buffer for file names (64KB should be enough for many files)
    max_file_buffer = 65536 
    file_buffer = ctypes.create_unicode_buffer(max_file_buffer)
    
    # Filter: Display Name\0Pattern\0...
    filter_str = "Image Files\0*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.exr;*.hdr;*.psd;*.tga\0All Files\0*.*\0\0"
    
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.hwndOwner = 0 
    ofn.lpstrFilter = filter_str
    ofn.lpstrFile = ctypes.cast(file_buffer, wintypes.LPWSTR)
    ofn.nMaxFile = max_file_buffer
    ofn.lpstrTitle = title
    ofn.Flags = OFN_ALLOWMULTISELECT | OFN_EXPLORER | OFN_FILEMUSTEXIST
    
    if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        # Parse the result buffer
        files = []
        current_str = ""
        i = 0
        while i < max_file_buffer:
            char = file_buffer[i]
            if char == '\0':
                if not current_str:
                    # Double null hit (empty string after a null) -> End of list
                    break
                files.append(current_str)
                current_str = ""
            else:
                current_str += char
            i += 1
            
        if not files:
            return []
            
        if len(files) == 1:
            return files # Single file full path
        else:
            # Multi-select: First element is directory, rest are filenames
            directory = files[0]
            return [os.path.join(directory, f) for f in files[1:]]
            
    return []

def remove_connections(node, port_id):
    """
    특정 노드의 특정 포트에 연결된 모든 연결을 제거합니다.
    텍스쳐 노드에 기존에 연결되어있던 scale, offset, rotate 노드의 연결을 제거합니다.
    
    Args:
        node (maxon.GraphNode): 대상 노드
        port_id (str): 대상 포트 ID
    """
    if not node or not node.IsValid():
        return

    input_ports = node.GetInputs().GetChildren() # 입력 포트 리스트
    for input_port in input_ports:
        port_name = input_port.GetId().ToString()
        if port_name == port_id:
            # 각 포트에 연결된 선(Connection) 가져오기
            connections = []
            input_port.GetConnections(maxon.PORT_DIR.INPUT, connections)
            for connection in connections:
                source_port = connection[0] # 연결된 소스 포트 (출력 포트)
                # RemoveConnection(source, destination)
                maxon.GraphModelHelper.RemoveConnection(source_port, input_port)
            break # 포트를 찾았으므로 루프 종료

def create_texture_node(graph, texture_path):
    """Creates a Texture Sampler node and sets the path."""
    tex_node = graph.AddChild(maxon.Id(), ID_RS_TEXTURESAMPLER)
    
    # Set Texture Path
    path_port = tex_node.GetInputs().FindChild(PORT_RS_TEX_PATH).FindChild("path")
    if path_port.IsValid():
        path_port.SetPortValue(texture_path)
    
    return tex_node

def find_standard_material_and_output(graph):
    """Finds the Standard Material and Output node in the graph."""
    standard_mat = None
    output_node = None
    
    root = graph.GetRoot()
    # GetInnerNodes to search recursively or just children of root?
    # Usually nodes are children of root.
    # Using GetInnerNodes as per user snippet suggestion
    for node in root.GetInnerNodes(mask=maxon.NODE_KIND.NODE, includeThis=False):
        asset_id = node.GetValue("net.maxon.node.attribute.assetid")[0]
        if asset_id == ID_RS_STANDARD_MATERIAL:
            standard_mat = node
        elif asset_id == ID_RS_OUTPUT:
            output_node = node
            
    return standard_mat, output_node

def main():
    # 1. Select Active Material in Node Editor
    c4d.CallCommand(300001026) # Deselect All Materials
    c4d.CallCommand(465002328) # Select Active Material in Node Editor
    
    doc = c4d.documents.GetActiveDocument()
    mat = doc.GetActiveMaterial()

    # 2. Check/Create Material
    if not mat:
        if c4d.gui.QuestionDialog("텍스처를 추가할 머티리얼 노드 에디터를 열어주세요.\n새로운 머티리얼을 생성하시겠습니까?"):
            # Create Redshift Material
            print("Create Redshift Material")
            c4d.CallCommand(1040264, 1012) # Materials > Redshift > Standard Material
            mat = doc.GetActiveMaterial()
            #c4d.EventAdd() # 해도 작동 안됨
            if not mat:
                return
        else:
            return

    nodeMaterial = mat.GetNodeMaterialReference()
    if not nodeMaterial.HasSpace(ID_RS_NODESPACE):
        c4d.gui.MessageDialog("선택한 머티리얼이 레드쉬프트 노드 머티리얼이 아닙니다.")
        return

    graph = nodeMaterial.GetGraph(ID_RS_NODESPACE)
    if graph.IsNullValue():
        return

    # 3. Find Standard Material
    standard_mat, output_node = find_standard_material_and_output(graph)
    
    if not standard_mat:
        c4d.gui.MessageDialog("Standard Material 노드를 찾을 수 없습니다.")
        return

    # 4. Load Textures (Windows API Multi-Select)
    texture_files = ask_open_filenames(title="텍스처 파일을 선택하세요")

    if not texture_files:
        return

    # 5. Process Textures
    created_nodes = []
    
    # Flags to prevent multiple connections to same channel
    connected_flags = {
        "base_color": False,
        "metalness": False,
        "refl_roughness": False,
        "opacity_color": False,
        "emission_color": False,
        "bump_input": False, # For both bump and normal
        "displacement": False
    }

    with graph.BeginTransaction() as transaction:
        for tex_path in texture_files:
            fname = os.path.basename(tex_path)
            
            # Detect Channel
            channel = IMfine_Utils.GetTextureChannel(fname)
            
            # Create Texture Node
            tex_node = create_texture_node(graph, tex_path)
            created_nodes.append(tex_node)
            
            # Rename Node based on channel or default
            node_name = "Texture"
            if channel:
                # CHANNEL_SUFFIXES 딕셔너리를 기반으로 노드 이름을 결정합니다.
                # 예: "base_color" -> "BaseColor"
                node_name = CHANNEL_SUFFIXES.get(channel, channel.replace("_", " ").title())
            
            tex_node.SetValue("net.maxon.node.base.name", node_name)
            
            if not channel:
                continue

            # Connect Logic
            tex_out = tex_node.GetOutputs().FindChild(PORT_RS_TEX_OUTCOLOR)
            
            # Helper to set Colorspace
            def set_colorspace_raw(node):
                tex0_port = node.GetInputs().FindChild(PORT_RS_TEX_PATH)
                if tex0_port.IsValid():
                    colorspace_port = tex0_port.FindChild("colorspace")
                    if colorspace_port.IsValid():
                        colorspace_port.SetPortValue(RS_INPUT_COLORSPACE_RAW)

            if channel == "base_color":
                if not connected_flags["base_color"]:
                    target = standard_mat.GetInputs().FindChild(PORT_RS_STD_BASE_COLOR)
                    if target.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_BASE_COLOR)
                        tex_out.Connect(target)
                        connected_flags["base_color"] = True
                    
            elif channel == "metalness":
                set_colorspace_raw(tex_node)
                if not connected_flags["metalness"]:
                    target = standard_mat.GetInputs().FindChild(PORT_RS_STD_METALNESS)
                    if target.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_METALNESS)
                        tex_out.Connect(target)
                        connected_flags["metalness"] = True
                    
            elif channel == "refl_roughness":
                set_colorspace_raw(tex_node)
                if not connected_flags["refl_roughness"]:
                    target = standard_mat.GetInputs().FindChild(PORT_RS_STD_ROUGHNESS)
                    if target.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_ROUGHNESS)
                        tex_out.Connect(target)
                        connected_flags["refl_roughness"] = True
                    
            elif channel == "opacity_color":
                set_colorspace_raw(tex_node)
                if not connected_flags["opacity_color"]:
                    target = standard_mat.GetInputs().FindChild(PORT_RS_STD_OPACITY)
                    if target.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_OPACITY)
                        tex_out.Connect(target)
                        connected_flags["opacity_color"] = True
            
            elif channel == "emission_color":
                if not connected_flags["emission_color"]:
                    target = standard_mat.GetInputs().FindChild(PORT_RS_STD_EMISSION)
                    if target.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_EMISSION)
                        tex_out.Connect(target)
                        connected_flags["emission_color"] = True
                    
            elif channel == "normal":
                set_colorspace_raw(tex_node)
                # Create Bump Map Node (Type 1001 for Tangent Space Normal)
                if not connected_flags["bump_input"]:
                    bump_node = graph.AddChild(maxon.Id(), ID_RS_BUMPMAP)
                    created_nodes.append(bump_node)
                    bump_node.SetValue("net.maxon.node.base.name", "Normal Map")
                    
                    # Set Input Type to 1001 (Tangent-Space Normal)
                    bump_type_port = bump_node.GetInputs().FindChild(PORT_RS_BUMP_TYPE)
                    if bump_type_port.IsValid():
                        bump_type_port.SetPortValue(1) # Normal
                        
                    
                    # Connect Texture -> Bump Node
                    bump_in = bump_node.GetInputs().FindChild(PORT_RS_BUMP_INPUT)
                    if bump_in.IsValid():
                        # Newly created node, no need to remove connections
                        tex_out.Connect(bump_in)
                    
                    # Connect Bump Node -> Standard Material
                    bump_out = bump_node.GetOutputs().FindChild(PORT_RS_BUMP_OUT)
                    std_bump_in = standard_mat.GetInputs().FindChild(PORT_RS_STD_BUMP_INPUT)
                    if bump_out.IsValid() and std_bump_in.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_BUMP_INPUT)
                        bump_out.Connect(std_bump_in)
                        connected_flags["bump_input"] = True

            elif channel == "bump":
                set_colorspace_raw(tex_node)
                # Create Bump Map Node (Type 1000 for Height Field)
                if not connected_flags["bump_input"]:
                    bump_node = graph.AddChild(maxon.Id(), ID_RS_BUMPMAP)
                    created_nodes.append(bump_node)
                    bump_node.SetValue("net.maxon.node.base.name", "Bump Map")
                    
                    # Set Input Type to 1000
                    bump_type_port = bump_node.GetInputs().FindChild(PORT_RS_BUMP_TYPE)
                    if bump_type_port.IsValid():
                        bump_type_port.SetPortValue(0) # Bump
                    
                    # Connect Texture -> Bump Node
                    bump_in = bump_node.GetInputs().FindChild(PORT_RS_BUMP_INPUT)
                    if bump_in.IsValid():
                        # Newly created node, no need to remove connections
                        tex_out.Connect(bump_in)
                    
                    # Connect Bump Node -> Standard Material
                    bump_out = bump_node.GetOutputs().FindChild(PORT_RS_BUMP_OUT)
                    std_bump_in = standard_mat.GetInputs().FindChild(PORT_RS_STD_BUMP_INPUT)
                    if bump_out.IsValid() and std_bump_in.IsValid():
                        remove_connections(standard_mat, PORT_RS_STD_BUMP_INPUT)
                        bump_out.Connect(std_bump_in)
                        connected_flags["bump_input"] = True

            elif channel == "displacement":
                set_colorspace_raw(tex_node)
                if not connected_flags["displacement"] and output_node:
                    disp_node = graph.AddChild(maxon.Id(), ID_RS_DISPLACEMENT)
                    created_nodes.append(disp_node)
                    disp_node.SetValue("net.maxon.node.base.name", "Displacement")
                    
                    # Connect Texture -> Displacement Node
                    disp_in = disp_node.GetInputs().FindChild(PORT_RS_DISP_TEXMAP)
                    if disp_in.IsValid():
                        # Newly created node, no need to remove connections
                        tex_out.Connect(disp_in)
                    
                    # Connect Displacement Node -> Output Node
                    disp_out = disp_node.GetOutputs().FindChild(PORT_RS_DISP_OUT)
                    out_disp_in = output_node.GetInputs().FindChild(PORT_RS_OUTPUT_DISPLACEMENT)
                    if disp_out.IsValid() and out_disp_in.IsValid():
                        remove_connections(output_node, PORT_RS_OUTPUT_DISPLACEMENT)
                        disp_out.Connect(out_disp_in)
                        connected_flags["displacement"] = True

        # 6. Select and Arrange (Moved inside transaction)
        # Deselect all first
        maxon.GraphModelHelper.DeselectAll(graph, maxon.NODE_KIND.NODE)
        
        # Select created nodes
        for node in created_nodes:
            if node.IsValid():
                maxon.GraphModelHelper.SelectNode(node)
        
        if standard_mat.IsValid():
            maxon.GraphModelHelper.SelectNode(standard_mat)
        if output_node.IsValid():
            maxon.GraphModelHelper.SelectNode(output_node)

        transaction.Commit()
    
    # Arrange (Outside transaction)
    c4d.CallCommand(465002311) # Arrange Selected Nodes
    c4d.EventAdd()

if __name__ == "__main__":
    main()
