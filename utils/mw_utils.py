import c4d # 모듈이여도 c4d는 항상 필요
import maxon
import os
import re

def remove_connections(node, port_id):
    """
    특정 노드의 특정 포트에 연결된 모든 연결을 제거합니다.
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




def GetAllObjects(doc):
    """
    씬 내의 모든 오브젝트를 리스트로 반환합니다.
    """
    result = []
    def _collect(obj):
        while obj:
            result.append(obj)
            _collect(obj.GetDown())
            obj = obj.GetNext()
            
    _collect(doc.GetFirstObject())
    return result

def GetObjectsInLayer(doc, layer_obj):
    """
    주어진 레이어(layer_obj)에 할당된 모든 오브젝트를 리스트로 반환합니다.
    """
    all_objs = GetAllObjects(doc)
    return [obj for obj in all_objs if obj.GetLayerObject(doc) == layer_obj]

def GetAllChildren(objects, parent=True) -> list:
    """
    입력값은 단일 오브젝트 또는 오브젝트 리스트 모두 허용합니다.
    반환값은 항상 오브젝트들의 리스트입니다.
    (Accepts single object or list of objects, always returns a list)

    :param objects: 부모 오브젝트 또는 오브젝트 리스트 :type objects: c4d.BaseObject | list[c4d.BaseObject]
    :return: 자식 오브젝트들을 포함한 리스트 :rtype: list[c4d.BaseObject]
    """
    if objects is None:
        return []
    objs = objects if isinstance(objects, list) else [objects]
    
    children = []
    for o in objs:
        if o is None:
            continue
        if parent: children.append(o)
        child = o.GetDown()
        while child:
            children.extend(GetAllChildren(child))
            child = child.GetNext()
    return children

def GetFullCache(objects, parent=True, deform=True, children=True) -> list:
    """
    입력값은 단일 오브젝트 또는 오브젝트 리스트 모두 허용합니다.
    DeformCache, Cache, 하위 오브젝트까지 재귀적으로 탐색하여 모든 메쉬를 리스트로 반환합니다.
    deform=False로 지정하면 DeformCache는 무시하고 Cache만 탐색합니다. (최적화용)
    (Accepts single object or list of objects, always returns a list of meshes including Cache and children. If deform=False, ignores DeformCache.)

    :param objects: 오브젝트 또는 오브젝트 리스트 :type objects: c4d.BaseObject | list[c4d.BaseObject]
    :param parent: 입력 오브젝트도 결과에 포함할지 여부 :type parent: bool
    :param deform: DeformCache도 탐색할지 여부 :type deform: bool
    :param children: 자식 오브젝트도 탐색할지 여부 :type children: bool
    :return: 최종 캐시 메쉬 오브젝트 리스트 :rtype: list[c4d.PointObject]
    """
    # print("objects:", objects)
    if objects is None:
        return []
    object_list = objects if isinstance(objects, list) else [objects]
    result_meshes = []

    def _recurse(current_obj):
        if current_obj is None:
            return
        # DeformCache 우선 (옵션)
        if deform:
            deform_cache = current_obj.GetDeformCache()
            if deform_cache is not None:
                _recurse(deform_cache)
                # 하위 오브젝트는 DeformCache 내부에서만 탐색
                return
        cache_obj = current_obj.GetCache()
        if cache_obj is not None:
            _recurse(cache_obj)
        else:
            if not current_obj.GetBit(c4d.BIT_CONTROLOBJECT): # 제너레이터로 생성된 오브젝트는 무시
                if current_obj.IsInstanceOf(c4d.Opolygon):
                    result_meshes.append(current_obj)
        
        # 하위 오브젝트 재귀
        if children:
            child_obj = current_obj.GetDown()
            while child_obj is not None:
                _recurse(child_obj)
                child_obj = child_obj.GetNext()

    for root_obj in object_list:
        if parent:
            _recurse(root_obj)
        else:
            # parent=False면 하위만 탐색
            if children:
                child_obj = root_obj.GetDown()
                while child_obj is not None:
                    _recurse(child_obj)
                    child_obj = child_obj.GetNext()
    return result_meshes

TEXTURE_CHANNELS = {
    "base_color":        [
        "basecolor", "base", "color", "albedo", "diffuse", "diff", 
        "col", "bc", "alb", "rgb" , "d"
    ],
    "normal":       [
        "normal", "norm", "nrm", "nml", "nrml", "n" 
    ],
    "bump":         [
        "bump", "b"
    ],
    "ao":           [
        "ao", "ambient", "occlusion", "occ", "amb"
    ],
    "metalness":    [
        "metallic", "metalness", "metal", "mtl", "met", "m"
    ],
    "refl_roughness":    [
        "roughness", "rough", "rgh", "r"
    ],
    "refl_weight":     [
        "specular", "spec", "s", "refl", "reflection"
    ],
    "glossiness":   [
        "glossiness", "gloss", "g"
    ],
    "opacity_color":      [
        "opacity", "opac", "alpha", "transparency", "transparent", 
        "o", "a", "mask", "cutout" # 알파 마스크용 용어 추가
    ],
    "translucency": [
        "translucency", "transmission", "trans", 
        "sss", "subsurface", "scatter", "scattering" # SSS 관련 용어 보강
    ],
    "displacement": [
        "displacement", "disp", "dsp", 
        "height", "h"
    ],
    "emission_color":     [
        "emissive", "emission", "emit", "illu", "illumination", "selfillum"
    ]
}

def _split_into_components(fname):
    """
    Split filename into components with prefix filtering
    'D_Wood_Maple_01_ROUGH_1.jpg' -> ['wood', 'maple', 'rough']
    """
    # Remove extension
    fname = os.path.splitext(fname)[0]

    # [NEW] Discard prefix: Keep string only after the LAST underscore
    if "_" in fname:
        # 마지막 _ 뒤의 부분만 가져옴
        fname = fname.rsplit("_", 1)[-1]
    else:
        # 언더바가 없으면 조건에 맞지 않으므로 빈 리스트 반환
        return []

    # Remove digits
    fname = "".join(i for i in fname if not i.isdigit())

    # Separate CamelCase by space
    fname = re.sub(r"([a-z])([A-Z])", r"\g<1> \g<2>", fname)

    # Replace common separators with SPACE
    separators = ["_", ".", "-", "__", "--", "#"]
    for sep in separators:
        fname = fname.replace(sep, " ")

    components = fname.split(" ")
    components = [c.lower() for c in components if c.strip()]
    return components

def GetTextureChannel(fname):
    """
    파일명의 마지막 '_' 뒤의 단어를 추출하여 채널을 판별합니다.
    점수 계산 없이 정확히 일치하는 키워드가 있으면 해당 채널을 반환합니다.
    """
    # 1. 확장자 제거
    base_name = os.path.splitext(fname)[0]
    
    # 2. '_'가 없으면 판별 불가
    if "_" not in base_name:
        return None
        
    # 3. 마지막 '_' 뒤의 단어 추출 및 소문자 변환
    suffix = base_name.rsplit("_", 1)[-1].lower()
    
    # 4. 채널 매칭 확인
    for channel, keywords in TEXTURE_CHANNELS.items():
        if suffix in keywords:
            return channel
            
    return None


def GetMergedObject(self, op, doc): #Deprecated
    """Create a merged clone of all input objects in a dummy document and return that merged object."""
    null = c4d.BaseObject(c4d.Onull)

    for node in op:
        aliastrans = c4d.AliasTrans()
        if not aliastrans or not aliastrans.Init(doc):
            return False
        if node.GetUp() is None:
            clone = node.GetClone(c4d.COPYFLAGS_NONE, aliastrans)
            clone.InsertUnderLast(null)
        elif node.GetUp() is not None:
            tempParent = c4d.BaseObject(c4d.Onull)
            tempParent.SetMg(node.GetUp().GetMg())
            clone = node.GetClone(c4d.COPYFLAGS_NONE, aliastrans)
            clone.InsertUnderLast(tempParent)
            tempParent.InsertUnderLast(null)
        aliastrans.Translate(True)

    doc.InsertObject(null)

    # The settings of the 'Join' tool.
    bc = c4d.BaseContainer()
    # Merge possibly existing selection tags.
    bc[c4d.MDATA_JOIN_MERGE_SELTAGS] = True

    # Execute the Join command in the dummy document.
    res = c4d.utils.SendModelingCommand(command=c4d.MCOMMAND_JOIN, 
                                        list=[null], 
                                        mode=c4d.MODELINGCOMMANDMODE_ALL, 
                                        bc=bc, 
                                        doc=doc, 
                                        flags=c4d.MODELINGCOMMANDFLAGS_CREATEUNDO)
    if not res:
        raise RuntimeError("Modelling command failed.")

    # The 'Join' command returns its result in the return value of SendModelingCommand()
    joinResult = res[0].GetClone()
    res[0].Remove()
    null.Remove() # Remove the null object from the dummy document.

    if not isinstance(joinResult, c4d.BaseObject):
        raise RuntimeError("Unexpected return value for Join tool.")
    if not isinstance(joinResult, c4d.PointObject):
        raise RuntimeError("Return value is not a point object.")

    return joinResult


def SelectObjects(objects, doc):
    c4d.CallCommand(12113)  # Deselect All
    for obj in objects:
        doc.AddUndo(c4d.UNDOTYPE_BITS, obj)  # 언도 추가
        doc.SetSelection(obj , mode=c4d.SELECTION_ADD)
    c4d.EventAdd()  # 뷰포트 업데이트