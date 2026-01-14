import c4d
import maxon
import os
import json

# --- 상수 및 ID ---
# 노드 ID
ID_RS_TEXTURESAMPLER = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.texturesampler")
ID_RS_MATH_ABS = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsmathabs")
ID_RS_MATH_ABS_VECTOR = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.rsmathabsvector")
ID_RS_TRIPLANAR = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.triplanar")
ID_RS_STANDARD_MATERIAL = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.standardmaterial")

# 포트 ID (공통)
# Abs 및 AbsVector 출력은 연결 로직에서 유사하지만, 필요한 경우 정확하게 구분해야 합니다.
# 실제로 AbsVector 출력 ID는 약간 다를 수 있으며, 보통 "out" 또는 "outColor"입니다. 동적으로 확인하거나 표준 "out"을 사용합니다.
# RS Math 노드의 경우 출력은 종종 단순히 "out"입니다.

# 텍스처 샘플러 포트
PORT_TEX_SCALE = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.scale"
PORT_TEX_OFFSET = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.offset"
PORT_TEX_ROTATE = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.rotate"
PORT_TEX_OUTCOLOR = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor"

# Triplanar 포트
PORT_TRI_IMAGE_X = "com.redshift3d.redshift4c4d.nodes.core.triplanar.imagex"
PORT_TRI_SCALE = "com.redshift3d.redshift4c4d.nodes.core.triplanar.scale"
PORT_TRI_OFFSET = "com.redshift3d.redshift4c4d.nodes.core.triplanar.offset"
PORT_TRI_ROTATE = "com.redshift3d.redshift4c4d.nodes.core.triplanar.rotation"
PORT_TRI_OUTCOLOR = "com.redshift3d.redshift4c4d.nodes.core.triplanar.outcolor"

# Abs 포트
PORT_ABS_INPUT = "com.redshift3d.redshift4c4d.nodes.core.rsmathabs.input"
PORT_ABS_OUT = "com.redshift3d.redshift4c4d.nodes.core.rsmathabs.out"

# AbsVector 포트
PORT_ABS_VECTOR_INPUT = "com.redshift3d.redshift4c4d.nodes.core.rsmathabsvector.input"
PORT_ABS_VECTOR_OUT = "com.redshift3d.redshift4c4d.nodes.core.rsmathabsvector.out"

# 다이얼로그 ID
GRP_MAIN = 1000
GRP_TRANSFORM = 1001
GRP_SCALE = 1002
GRP_SCALE_TYPE = 1003
GRP_RADIO_SCALE_TYPE = 1004
CHK_SCALE = 1005
CHK_OFFSET = 1006
CHK_ROTATION = 1007
CHK_TRIPLANAR = 1008
CHK_PER_TEXTURE = 1009

RAD_ABS = 1010
RAD_VEC_ABS = 1011
BTN_APPLY = 1012
BTN_CLOSE = 1013


def get_script_metadata():
    """스크립트 메타데이터 반환"""
    return {
        "name": "Quick Texture Transform",
        "description": "선택한 텍스처 노드를 컨트롤 할 수 있는 노드를 빠르게 구성합니다.",
        "tags": ["Material", "Texture", "UV", "Redshift"],
        "icon": "IMfine_Quick_Texture_Transform.tif"
    }


class TextureTransformDialog(c4d.gui.GeDialog):
    def __init__(self):
        self.params = {
            "scale": True,
            "offset": False,
            "rotation": False,
            "triplanar": True,
            "scale_type_vector": False, # False = Abs, True = Vector Abs
            "per_texture": False
        }
        self.settings_file = os.path.join(os.path.dirname(__file__), "IMfine_Settings.json")

    def load_settings(self):
        """설정 파일에서 값을 불러옵니다."""
        if not os.path.exists(self.settings_file):
            return

        try:
            with open(self.settings_file, 'r') as f:
                all_settings = json.load(f)
                
            # QuickTextureTransform 키가 있는지 확인
            if "QuickTextureTransform" in all_settings:
                saved_params = all_settings["QuickTextureTransform"]
                # 저장된 값이 있으면 params 업데이트
                for key, value in saved_params.items():
                    if key in self.params:
                        self.params[key] = value
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """현재 설정을 파일에 저장합니다."""
        
        try:
            all_settings = {}
            # 기존 설정 읽기
            if os.path.exists(self.settings_file):
                 try:
                    with open(self.settings_file, 'r') as f:
                        all_settings = json.load(f)
                 except:
                     pass # 파일 읽기 실패 시 빈 딕셔너리 사용

            # 현재 설정 업데이트
            all_settings["QuickTextureTransform"] = self.params

            with open(self.settings_file, 'w') as f:
                json.dump(all_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def CreateLayout(self):
        self.SetTitle("Quick Texture Transform")

        self.GroupBegin(GRP_MAIN, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 1, 0, "Controls", 0)
        self.GroupBorderSpace(10, 5, 10, 5)

        # Scale 체크박스
        self.AddCheckbox(CHK_SCALE, c4d.BFH_LEFT, 0, 0, "Scale")
        
        # Scale 타입 그룹 (공백 추가)
        self.GroupBegin(GRP_SCALE_TYPE, c4d.BFH_SCALEFIT | c4d.BFV_TOP, 2, 0, "Scale Type", 0)
        self.GroupBorderSpace(15, 0, 0, 0)
        # Scale 타입을 위한 라디오 그룹
        self.AddRadioGroup(GRP_RADIO_SCALE_TYPE, c4d.BFH_LEFT | c4d.BFV_TOP, 2, 0)
        self.AddChild(GRP_RADIO_SCALE_TYPE, RAD_ABS, "Abs")
        self.AddChild(GRP_RADIO_SCALE_TYPE, RAD_VEC_ABS, "Vector Abs")
        self.GroupEnd()
        
        self.AddCheckbox(CHK_OFFSET, c4d.BFH_LEFT | c4d.BFV_TOP, 0, 0, "Offset")
        self.AddCheckbox(CHK_ROTATION, c4d.BFH_LEFT | c4d.BFV_TOP, 0, 0, "Rotation")
        
        self.AddSeparatorH(c4d.BFH_SCALEFIT)
        
        self.AddCheckbox(CHK_TRIPLANAR, c4d.BFH_LEFT | c4d.BFV_TOP, 0, 0, "Use Triplanar")
        self.AddCheckbox(CHK_PER_TEXTURE, c4d.BFH_LEFT | c4d.BFV_TOP, 0, 0, "Create Abs per Texture")
        
        # 버튼
        if self.GroupBegin(0, c4d.BFH_CENTER, 2, 0, "", 0):
            self.GroupBorderSpace(0, 10, 0, 0)
            self.AddButton(BTN_APPLY, c4d.BFH_SCALEFIT, 100, 0, "Apply")
            self.AddButton(BTN_CLOSE, c4d.BFH_SCALEFIT, 100, 0, "Close")
        self.GroupEnd()
    
        self.GroupEnd() # GRP_MAIN
        return True

    def InitValues(self):
        self.load_settings() # 설정 불러오기

        self.SetBool(CHK_SCALE, self.params["scale"])
        self.SetBool(CHK_OFFSET, self.params["offset"])
        self.SetBool(CHK_ROTATION, self.params["rotation"])
        self.SetBool(CHK_TRIPLANAR, self.params["triplanar"])
        self.SetBool(CHK_PER_TEXTURE, self.params["per_texture"])
        
        # Scale Type 설정 (Vector 여부에 따라 라디오 버튼 선택)
        if self.params["scale_type_vector"]:
            self.SetInt32(GRP_RADIO_SCALE_TYPE, RAD_VEC_ABS)
        else:
            self.SetInt32(GRP_RADIO_SCALE_TYPE, RAD_ABS)
            
        # UI 활성화 상태 업데이트
        self.Enable(RAD_ABS, self.params["scale"])
        self.Enable(RAD_VEC_ABS, self.params["scale"])
        
        return True

    def Command(self, id, msg):
        if id == CHK_SCALE:
            self.Enable(RAD_ABS, self.GetBool(CHK_SCALE))
            self.Enable(RAD_VEC_ABS, self.GetBool(CHK_SCALE))

        if id == BTN_CLOSE:
            self.Close()
            return True
            
        elif id == BTN_APPLY:
            # 파라미터 업데이트
            self.params["scale"] = self.GetBool(CHK_SCALE)
            self.params["offset"] = self.GetBool(CHK_OFFSET)
            self.params["rotation"] = self.GetBool(CHK_ROTATION)
            self.params["triplanar"] = self.GetBool(CHK_TRIPLANAR)
            self.params["per_texture"] = self.GetBool(CHK_PER_TEXTURE)
            
            scale_type = self.GetInt32(GRP_RADIO_SCALE_TYPE)
            print(f"scale_type: {scale_type}")
            self.params["scale_type_vector"] = (scale_type == RAD_VEC_ABS)
            print(f"scale_type_vector: {self.params['scale_type_vector']}")
            
            # 설정 저장
            self.save_settings()
            
            # 검증 및 데이터 가져오기
            graph, texture_nodes = validate_selection(c4d.documents.GetActiveDocument())
            if not graph:
                return True

            # 로직 실행
            apply_texture_controls(graph, texture_nodes, self.params)
            # self.Close()
            return True
            
        return True


def get_port(node, port_id_string):
    """
    문자열 ID로 포트를 찾는 헬퍼 함수입니다.
    
    Args:
        node (maxon.Node): 노드
        port_id_string (str): 포트 ID 문자열
    
    Returns:
        maxon.Port: 포트
    """
    inputs = node.GetInputs()
    port = inputs.FindChild(port_id_string)
    if not port.IsValid():
        # 입력에서 찾지 못하면 출력에서 찾습니다 (보통 특정 방향을 찾지만)
        outputs = node.GetOutputs()
        port = outputs.FindChild(port_id_string)
    return port

def create_control_nodes(graph, params):
    """
    파라미터에 기반하여 제어 노드(Scale, Offset, Rotate)를 생성합니다.
    
    Args:
        graph (maxon.Graph): Redshift 그래프
        params (dict): 파라미터
    
    Returns:
        tuple: 생성된 노드들 (scale_node, offset_node, rotate_node, new_nodes)
    """
    scale_node = None
    offset_node = None
    rotate_node = None
    new_nodes = []
    
    # Scale Abs 노드 생성
    if params["scale"]:
        print(f"scale_type_vector: {params['scale_type_vector']}")
        if params["scale_type_vector"]:
            scale_node = graph.AddChild(maxon.Id(), ID_RS_MATH_ABS_VECTOR)
        else:
            scale_node = graph.AddChild(maxon.Id(), ID_RS_MATH_ABS)

        if scale_node: 
            new_nodes.append(scale_node)
            scale_node.SetValue("net.maxon.node.base.name", "Scale Abs")

            # 기본값 1로 설정
            if params["scale_type_vector"]:
                scale_in = scale_node.GetInputs().FindChild(PORT_ABS_VECTOR_INPUT)
                scale_in.SetDefaultValue(maxon.Vector(1, 1, 1))
            else:
                scale_in = scale_node.GetInputs().FindChild(PORT_ABS_INPUT)
                scale_in.SetDefaultValue(1.0)

    # Offset Abs 노드 생성
    if params["offset"]:
        offset_node = graph.AddChild(maxon.Id(), ID_RS_MATH_ABS_VECTOR)
        if offset_node: 
            new_nodes.append(offset_node)
            offset_node.SetValue("net.maxon.node.base.name", "Offset Abs")

    # Rotation Abs 노드 생성
    if params["rotation"]:
        if params["triplanar"]: # Triplanar면 Vector Abs 노드 생성
            rotate_node = graph.AddChild(maxon.Id(), ID_RS_MATH_ABS_VECTOR)
        else:   # Triplanar이 아니면 Abs 노드 생성
            rotate_node = graph.AddChild(maxon.Id(), ID_RS_MATH_ABS)
        
        if rotate_node: 
            new_nodes.append(rotate_node)
            rotate_node.SetValue("net.maxon.node.base.name", "Rotation Abs")
            
    return scale_node, offset_node, rotate_node, new_nodes

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

def validate_selection(doc):
    """
    노드 에디터의 머티리얼을 선택하고 그래프와 텍스처 노드 리스트를 반환합니다.
    
    Returns:
        tuple: (graph, texture_nodes) 또는 (None, None)
    """
    c4d.CallCommand(465002328) # Node Editor 창에 띄워진 머티리얼 선택하기
    mat = doc.GetActiveMaterial() # 선택한 머티리얼 불러오기.
    if not mat:
        c4d.gui.MessageDialog("노드 에디터 창을 열고 텍스처 노드를 선택하세요.")
        return None, None

    nodeMaterial = mat.GetNodeMaterialReference() # 노드 머티리얼 가져오기
    redshiftNodeSpaceId = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")
    
    if not nodeMaterial.HasSpace(redshiftNodeSpaceId):
        c4d.gui.MessageDialog("선택한 머티리얼이 레드쉬프트 노드 머티리얼이 아닙니다.")
        return None, None

    graph = nodeMaterial.GetGraph(redshiftNodeSpaceId) # 노드 그래프 가져오기
    if graph.IsNullValue():
        return None, None

    # 선택된 노드 가져오기
    selected_nodes = []
    maxon.GraphModelHelper.GetSelectedNodes(graph, maxon.NODE_KIND.NODE, lambda node: selected_nodes.append(node) or True)

    if not selected_nodes:
        c4d.gui.MessageDialog("한 개 이상의 텍스쳐 노드를 선택해주세요.")
        return None, None

    # 텍스처 샘플러 노드 필터링
    texture_nodes = []
    for node in selected_nodes:
        asset_id = node.GetValue("net.maxon.node.attribute.assetid")[0]
        if asset_id == ID_RS_TEXTURESAMPLER:
            texture_nodes.append(node)

    if not texture_nodes:
        c4d.gui.MessageDialog("한 개 이상의 텍스쳐 노드를 선택해주세요.")
        return None, None
        
    return graph, texture_nodes

def apply_texture_controls(graph, texture_nodes, params): 
    """
    검증된 텍스처 노드들에 대해 컨트롤 노드를 생성하고 연결합니다.
    
    Args:
        graph (maxon.GraphModel): 노드 그래프
        texture_nodes (list): 대상 텍스처 노드 리스트
        params (dict): 설정 파라미터
    """

    # 트랜잭션 시작
    with graph.BeginTransaction() as transaction:
        # 1. 파라미터에 기반하여 제어 노드 생성
        created_nodes = []
        
        # 공통 노드 (Per Texture가 아닐 때 사용)
        common_scale_node = None
        common_offset_node = None
        common_rotate_node = None
        
        if not params["per_texture"]:
            common_scale_node, common_offset_node, common_rotate_node, new_nodes = create_control_nodes(graph, params)
            created_nodes.extend(new_nodes)
        
        for tex_node in texture_nodes:
            # Per Texture일 경우 루프 안에서 생성, 아니면 공통 노드 사용
            if params["per_texture"]:
                scale_node, offset_node, rotate_node, new_nodes = create_control_nodes(graph, params)
                created_nodes.extend(new_nodes)
            else:
                scale_node = common_scale_node
                offset_node = common_offset_node
                rotate_node = common_rotate_node
            # 2. 연결 로직
            
            # 인라인으로 안전하게 출력 포트를 가져오는 헬퍼 함수
            def get_node_output(node):
                if not node or not node.IsValid(): return None
                aid = node.GetValue("net.maxon.node.attribute.assetid")[0]
                if aid == ID_RS_MATH_ABS:
                    return node.GetOutputs().FindChild(PORT_ABS_OUT)
                elif aid == ID_RS_MATH_ABS_VECTOR:
                    return node.GetOutputs().FindChild(PORT_ABS_VECTOR_OUT)
                return None

            if params["triplanar"]: # Triplanar 체크 된 경우
                # a. 텍스처 출력의 기존 연결 기억
                tex_out_port = tex_node.GetOutputs().FindChild(PORT_TEX_OUTCOLOR)
                connections = []
                if tex_out_port.IsValid():
                    tex_out_port.GetConnections(maxon.PORT_DIR.OUTPUT, connections)
                    for target_port in connections: # 연결된 노드가 있으면 연결 해제
                        maxon.GraphModelHelper.RemoveAllConnections(tex_node)

                # b. Triplanar 노드 생성
                triplanar_node = graph.AddChild(maxon.Id(), ID_RS_TRIPLANAR)
                created_nodes.append(triplanar_node)
                
                # c. 텍스처 -> Triplanar ImageX 연결
                tri_image_x = triplanar_node.GetInputs().FindChild(PORT_TRI_IMAGE_X)
                if tex_out_port.IsValid() and tri_image_x.IsValid():
                    tex_out_port.Connect(tri_image_x)
                
                # d. 제어 노드 -> Triplanar 연결
                if scale_node:
                    scale_out = get_node_output(scale_node)
                    tri_scale = triplanar_node.GetInputs().FindChild(PORT_TRI_SCALE)
                    if scale_out and scale_out.IsValid() and tri_scale.IsValid():
                        scale_out.Connect(tri_scale)

                if offset_node:
                    offset_out = get_node_output(offset_node)
                    tri_offset = triplanar_node.GetInputs().FindChild(PORT_TRI_OFFSET)
                    if offset_out and offset_out.IsValid() and tri_offset.IsValid():
                        offset_out.Connect(tri_offset)
                        
                if rotate_node:
                    rotate_out = get_node_output(rotate_node)
                    tri_rotate = triplanar_node.GetInputs().FindChild(PORT_TRI_ROTATE)
                    if rotate_out and rotate_out.IsValid() and tri_rotate.IsValid():
                        rotate_out.Connect(tri_rotate)

                # e. 연결 복구 (Triplanar Out -> 원래 목적지)
                tri_out_port = triplanar_node.GetOutputs().FindChild(PORT_TRI_OUTCOLOR)
                if tri_out_port.IsValid():
                    for connection in connections:
                        target_port = connection[0] # 다른 노드의 입력 포트
                        tri_out_port.Connect(target_port)

            else: # Triplanar 체크 안된 경우
                # --- 시나리오 B: 직접 연결 ---
                
                if scale_node:
                    scale_out = get_node_output(scale_node)
                    tex_scale = tex_node.GetInputs().FindChild(PORT_TEX_SCALE)
                    if scale_out and scale_out.IsValid() and tex_scale.IsValid():
                        remove_connections(tex_node, PORT_TEX_SCALE)
                        scale_out.Connect(tex_scale)
                        
                if offset_node:
                    offset_out = get_node_output(offset_node)
                    tex_offset = tex_node.GetInputs().FindChild(PORT_TEX_OFFSET)
                    if offset_out and offset_out.IsValid() and tex_offset.IsValid():
                        remove_connections(tex_node, PORT_TEX_OFFSET)
                        offset_out.Connect(tex_offset)
                        
                if rotate_node:
                    rotate_out = get_node_output(rotate_node)
                    tex_rotate = tex_node.GetInputs().FindChild(PORT_TEX_ROTATE)
                    if rotate_out and rotate_out.IsValid() and tex_rotate.IsValid():
                        remove_connections(tex_node, PORT_TEX_ROTATE)
                        rotate_out.Connect(tex_rotate)

        for node in created_nodes: # 생성된 노드 선택
            if node.IsValid():
                maxon.GraphModelHelper.SelectNode(node)

        transaction.Commit()

    c4d.CallCommand(465002311) # Arrange Selected Nodes
    c4d.EventAdd()
    return True


def main():
    # Hack to keep an async dialog alive in a Script Manger environment, please do not do this in a
    # production environment.
    global dlg
    dlg = TextureTransformDialog()
    dlg.Open(c4d.DLG_TYPE_ASYNC, defaultw=250, defaulth=200)

if __name__ == "__main__":
    main()
