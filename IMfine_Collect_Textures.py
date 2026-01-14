import c4d
import maxon
import os # 파일 경로 처리에 필요한 모듈
import shutil # 파일 복사에 필요한 모듈
import sys

CHANNEL_SUFFIXES = {
    "diffuse_color": "BaseColor", # RS Material
    "base_color": "BaseColor", # Standard Material
    "normal": "Normal",
    # "ao": "AO",
    "refl_metalness": "Metalic", # RS Material    
    "metalness": "Metalic", # Standard Material
    "refl_roughness": "Roughness",
    "refl_weight": "Specular",
    # "glossiness": "Glossiness",
    "opacity_color": "Opacity",
    # "translucency": "Translucency",
    "bump" : "Bump",
    "displacement" : "Displacement",
    "emission_color" : "Emissive"
}


def get_script_metadata():
    """스크립트 메타데이터 반환"""
    return {
        "name": "Collect Textures",
        "description": "선택한 Redshift 머티리얼에 사용된 텍스처 파일을 지정된 폴더로 수집합니다.",
        "tags": ["Texture", "Material", "Redshift", "Asset Delivery"],
        "icon": "IMfine_Collect_Textures.tif"
    }


def trace_texture_usage(node, visited=None):
    """
    노드의 출력을 끝까지 추적하여 최종적으로 Standard Material의 어떤 채널에 연결되는지 찾아냅니다.
    """
    if visited is None:
        visited = set()
    
    # 무한 루프 방지 (이미 방문한 노드는 패스)
    # GetPath()는 노드의 고유 경로를 반환합니다.
    try:
        node_path = node.GetPath()
    except:
        return []

    if node_path in visited:
        return []
    visited.add(node_path)
    
    found_channels = []
    
    # Standard Material ID 및 Output Node ID
    idRSMaterial = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.material") # RS Material
    idStandardMaterial = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.standardmaterial") # Standard Material
    idOutputNode = maxon.Id("com.redshift3d.redshift4c4d.node.output") # Output 노드(Displacement 연결용)

    # --- Debug: Trace Start ---
    indent = "  " * len(visited)
    try:
        current_node_id = node.GetValue("net.maxon.node.attribute.assetid")[0].ToString()
    except:
        current_node_id = "Unknown Node"
    print(f"{indent}[Trace] 노드 추적 중: {current_node_id}")

    # 1. 현재 노드의 모든 출력 포트 가져오기
    # (GetOutputs().GetChildren()은 포트 리스트를 반환)
    output_ports = node.GetOutputs().GetChildren()

    for out_port in output_ports:
        port_name = out_port.GetId().ToString()
        # print(f"{indent}  [Trace] 출력 포트 검사: {port_name}")

        # 2. 각 포트에 연결된 선(Connection) 가져오기
        connections = []
        out_port.GetConnections(maxon.PORT_DIR.OUTPUT, connections)
        
        if not connections:
            # print(f"{indent}    -> 연결 없음")
            pass

        for connection in connections:
            target_port = connection[0] # 목적지 포트
            target_node = target_port.GetAncestor(maxon.NODE_KIND.NODE) # 목적지 노드 (Inputs 리스트가 아닌 진짜 노드 찾기)
            
            # 목적지 노드의 Asset ID 확인
            asset_id_tuple = target_node.GetValue("net.maxon.node.attribute.assetid")
            if asset_id_tuple is None:
                continue
            target_asset_id = asset_id_tuple[0]
            target_asset_id_str = target_asset_id.ToString()

            print(f"{indent}    -> 연결 발견! 목적지 노드: {target_asset_id_str}")

            # CASE 1: 최종 목적지 도착 (RS Material or Standard Material)
            if target_asset_id == idStandardMaterial or target_asset_id == idRSMaterial:
                port_id = target_port.GetId().ToString()
                # "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color" 형태에서 뒷부분만 추출
                if "." in port_id:
                    port_id = port_id.split(".")[-1]
                print(f"{indent}      [!!!] Standard Material 도달! 연결된 채널: {port_id}")

                # 만약 port_id가 "bump_input"이면
                if port_id == "bump_input":
                    try:
                        # 상위 노드(com.redshift3d.redshift4c4d.nodes.core.bumpmap) 검사
                        if node.GetValue("net.maxon.node.attribute.assetid")[0] == maxon.Id("com.redshift3d.redshift4c4d.nodes.core.bumpmap"):
                            # Input Map Type 검사 (1000: HeightField -> Bump, Others -> Normal)
                            input_type = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.bumpmap.inputtype").GetDefaultValue()
                            if input_type == 1000:
                                port_id = "bump"
                            else:
                                port_id = "normal"
                    except Exception as e:
                        print(f"{indent}      [Warning] Bump/Normal check failed: {e}")

                found_channels.append(port_id)
            
            # CASE 2: 최종 목적지 도착 (Output Node - Displacement 등)
            elif target_asset_id == idOutputNode:
                port_id = target_port.GetId().ToString()
                if "." in port_id:
                    port_id = port_id.split(".")[-1]
                if "displacement" in port_id.lower():
                    print(f"{indent}      [!!!] Output Node (Displacement) 도달!")
                    found_channels.append(port_id)

            # CASE 3: 중간 노드 (계속 추적)
            # (Splitter, Ramp, CC, Triplanar, Bump, Sprite 등 모든 중간 노드)
            else:
                print(f"{indent}      [>>>] 중간 노드 통과, 재귀 추적 시작...")
                # 재귀 호출: 중간 노드에서 다시 추적 시작
                sub_results = trace_texture_usage(target_node, visited)
                found_channels.extend(sub_results)

    return found_channels

def main():
    # 1. 폴더 경로 지정
    doc = c4d.documents.GetActiveDocument()
    doc_path = doc.GetDocumentPath()

    selected_path = c4d.storage.LoadDialog(
        type=c4d.FILESELECTTYPE_ANYTHING,
        title="텍스처를 저장할 폴더를 선택하세요",
        flags=c4d.FILESELECT_DIRECTORY,
        # def_path="" # 기본 경로 지정
    )
    
    if not selected_path: # 폴더 선택이 취소된 경우
        return

    base_tex_path = os.path.join(selected_path, "tex")
    if not os.path.exists(base_tex_path): # tex 폴더가 없는 경우 생성
        try:
            os.makedirs(base_tex_path)
        except OSError as e:
            c4d.gui.MessageDialog(f"폴더 생성 실패: {e}")
            return

    
    redshiftNodeSpaceId = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace") # Redshift Node Space ID
    idTextureNode = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.texturesampler") # Texture Sampler Asset ID

    materials = doc.GetActiveMaterials()
    if not materials: # 선택된 머티리얼이 없는 경우
        c4d.gui.MessageDialog("선택된 머티리얼이 없습니다.")
        return

    # --- Phase 1: Collect Nodes ---
    collected_nodes = []

    for mat in materials:
        # Redshift Node Material인지 확인
        nodeMaterial = mat.GetNodeMaterialReference()
        
        # HasSpace로 그래프 존재 여부 확인
        if not nodeMaterial.HasSpace(redshiftNodeSpaceId): # Redshift Node Material이 아닌 경우
            continue
            
        graph = nodeMaterial.GetGraph(redshiftNodeSpaceId)
        if graph.IsNullValue(): # 그래프가 없는 경우
            continue

        mat_name = mat.GetName()
        root = graph.GetViewRoot()
        print(f"머티리얼 스캔 중: {mat_name}")

        # GetInnerNodes를 사용하여 그래프 내 모든 노드 순회
        for node in root.GetInnerNodes(mask=maxon.NODE_KIND.NODE, includeThis=False):
            # Asset ID 확인
            asset_id_tuple = node.GetValue("net.maxon.node.attribute.assetid")
            
            if asset_id_tuple is None:
                continue
            
            try:
                asset_id = asset_id_tuple[0]
            except (TypeError, IndexError):
                continue

            if asset_id != idTextureNode: # 텍스처 샘플러가 아닌 경우
                continue
            
            # tex0 포트 찾기
            tex0_port = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
            if not tex0_port.IsValid():
                # print(f"    tex0 포트가 유효하지 않습니다.")
                continue
            
            # path 포트 찾기
            path_port = tex0_port.FindChild("path")
            if not path_port.IsValid():
                # print(f"    path 포트가 유효하지 않습니다.")
                continue
            
            # 텍스처 경로 가져오기 (maxon.Url 또는 str)
            texture_path_val = path_port.GetDefaultValue()
            
            if texture_path_val is None:
                # print(f"    텍스처 경로 값을 찾을 수 없습니다.")
                continue
                
            texture_path = str(texture_path_val)
            
            if isinstance(texture_path_val, maxon.Url): # maxon.Url 객체인 경우 처리
                texture_path = texture_path_val.GetSystemPath()
            
            if not texture_path:
                # print(f"    텍스처 경로가 비어 있습니다.")
                continue
            
            # Store collected info
            collected_nodes.append({
                "mat_name": mat_name,
                "node": node,
                "texture_path": texture_path
            })

    # --- Phase 2: Process Collected Nodes ---
    success_materials = set()
    total_texture_count = 0
    
    print(f"총 {len(collected_nodes)}개의 텍스처 노드가 감지되었습니다. 처리를 시작합니다...")

    for item in collected_nodes:
        mat_name = item["mat_name"]
        node = item["node"]
        texture_path = item["texture_path"]
        
        print(f"! 처리 중: {mat_name} - {texture_path}")

        # --- Debug: Trace Texture Connections ---
        connected_channels = trace_texture_usage(node)
        if connected_channels:
            print(f"    [DEBUG] 연결된 채널: {list(set(connected_channels))}")
        else:
            print(f"    [DEBUG] 연결된 채널 없음 (또는 추적 실패)")
        # ----------------------------------------

        # 텍스처 파일 존재 여부 확인 및 경로 보정
        if not (os.path.isfile(texture_path)):
            path_found = False
            # 1. doc_path + texture_path
            if doc_path:
                cand1 = os.path.join(doc_path, texture_path)
                if os.path.exists(cand1) and os.path.isfile(cand1):
                    texture_path = cand1
                    path_found = True
            
            # 2. doc_path + "tex" + texture_path
            if not path_found and doc_path:
                cand2 = os.path.join(doc_path, "tex", texture_path)
                if os.path.exists(cand2) and os.path.isfile(cand2):
                    texture_path = cand2
                    path_found = True
                    
            if not path_found:
                print(f"    텍스처 파일이 존재하지 않거나 파일이 아닙니다: {texture_path}")
                continue

        # 파일명 설정 및 중복 처리
        original_file_name = os.path.basename(texture_path)
        name, ext = os.path.splitext(original_file_name)
        
        # 텍스처 채널 감지
        channel_key = None
        if connected_channels:
            channel_key = connected_channels[0]
        
        suffix = "Texture"
        if channel_key:
            if channel_key in CHANNEL_SUFFIXES:
                suffix = CHANNEL_SUFFIXES[channel_key]
            else:
                suffix = channel_key.title()

        # 머티리얼 이름 안전하게 변환
        safe_mat_name = "".join(c if c.isalnum() or c == '_' else '_' for c in mat_name).strip('_')
        if not safe_mat_name:
            safe_mat_name = "MaterialNameError"
        
        # 새로운 파일명 생성
        new_file_name = f"{safe_mat_name}_{suffix}{ext}"
        dest_path = os.path.join(base_tex_path, new_file_name)
        
        # 중복 파일명 처리
        counter = 0
        while os.path.exists(dest_path):
            new_file_name = f"{safe_mat_name}_{suffix}_{counter:02d}{ext}"
            dest_path = os.path.join(base_tex_path, new_file_name)
            counter += 1
        
        try:
            shutil.copy2(texture_path, dest_path)
            total_texture_count += 1
            success_materials.add(mat_name)
            item["texture_path"] = dest_path
        except Exception as e:
            print(f"    복사 실패: {original_file_name} - {e}")
    
    c4d.EventAdd()
    
    if c4d.gui.QuestionDialog(
        f"{len(success_materials)}개의 머티리얼에서 총 {total_texture_count}개의 텍스처를 수집했습니다." 
        f"\n저장 경로: {base_tex_path}"
        f"\n\n텍스쳐 경로를 저장한 경로로 변경하시겠습니까?"):
        
        for item in collected_nodes:
            mat_name = item["mat_name"]
            node = item["node"]
            texture_path = item["texture_path"]
            
            # 텍스처 경로를 저장한 경로로 변경
            tex0_port = node.GetInputs().FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
            if tex0_port.IsValid():
                path_port = tex0_port.FindChild("path")
                if path_port.IsValid():
                    graph = node.GetGraph() # 그래프 가져오기
                    with graph.BeginTransaction() as transaction: # 트랜젝션 시작해야 수정 가능
                        path_port.SetPortValue(texture_path)
                        transaction.Commit()
        c4d.EventAdd()


if __name__ == "__main__":
    main()
