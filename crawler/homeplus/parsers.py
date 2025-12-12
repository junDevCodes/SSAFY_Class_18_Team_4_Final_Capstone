"""
홈플러스 상품/카테고리 응답 파서 모듈

API 응답(JSON)에서 ProductData 스키마에 맞는 필드를 추출하는 로직을 담는다.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GrainCategory:
    """쌀/잡곡 카테고리 조합"""

    rcateNm: str
    lcateNm: str
    mcateNm: Optional[str]
    scateNm: Optional[str]
    lcateCd: Optional[int]
    mcateCd: Optional[int]
    scateCd: Optional[int]


def extract_grain_categories(map_json: Dict[str, Any]) -> List[GrainCategory]:
    """카테고리 맵에서 쌀/잡곡 계열 노드를 추출한다."""
    results: List[GrainCategory] = []

    def _get_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """자식 노드 리스트를 반환한다."""
        for key in ("children", "childList", "list", "categoryList", "middleCategoryList", "largeCategoryList"):
            if key in node and isinstance(node[key], list):
                return node[key]
        return []

    def _walk(node: Dict[str, Any], parent_path: Dict[str, Any]):
        """재귀적으로 트리를 순회하며 쌀/잡곡 노드를 수집한다."""
        cate_depth = str(node.get("cateDepth") or "").upper()
        cate_cd = node.get("cateCd") or node.get("id") or node.get("gcateCd")
        cate_nm = node.get("cateNm") or node.get("name")

        path = dict(parent_path)
        children = _get_children(node)
        has_scate_child = any(str(child.get("cateDepth") or "").upper() == "S" for child in children)
        if cate_depth in ("R", "L"):
            path["lcateNm"] = cate_nm
            path["lcateCd"] = _to_int(cate_cd)
        elif cate_depth == "M":
            path["mcateNm"] = cate_nm
            path["mcateCd"] = _to_int(cate_cd)
        elif cate_depth == "S":
            path["scateNm"] = cate_nm
            path["scateCd"] = _to_int(cate_cd)

        # lcateNm 이 쌀/잡곡이면 하위 조합을 결과로 수집
        should_collect = False
        if path.get("lcateNm") == "쌀/잡곡":
            if path.get("scateNm"):
                should_collect = True
            elif path.get("mcateNm") and not has_scate_child:
                should_collect = True

        if should_collect:
            results.append(
                GrainCategory(
                    rcateNm=path.get("rcateNm") or path.get("lcateNm") or "쌀/잡곡",
                    lcateNm=path.get("lcateNm") or "쌀/잡곡",
                    mcateNm=path.get("mcateNm"),
                    scateNm=path.get("scateNm"),
                    lcateCd=path.get("lcateCd"),
                    mcateCd=path.get("mcateCd"),
                    scateCd=path.get("scateCd"),
                )
            )

        for child in children:
            _walk(child, path)

    roots = _extract_roots(map_json)
    for root in roots:
        _walk(root, {"rcateNm": root.get("rcateNm") or root.get("cateNm")})

    return _deduplicate_grain(results)


def _extract_roots(map_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """카테고리 맵 응답에서 루트 노드 리스트를 추출한다."""
    if isinstance(map_json, list):
        return map_json
    if isinstance(map_json, dict):
        data = map_json.get("data")
        if isinstance(data, dict) and isinstance(data.get("categoryList"), list):
            return data["categoryList"]
    for key in ("data", "list", "categories", "rootList", "categoryList"):
        if key in map_json and isinstance(map_json[key], list):
            return map_json[key]
    return []


def _to_int(value: Any) -> Optional[int]:
    """정수 변환 헬퍼"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _deduplicate_grain(items: List[GrainCategory]) -> List[GrainCategory]:
    """중복 쌀/잡곡 조합을 제거한다."""
    seen = {}
    for item in items:
        key = (item.lcateCd, item.mcateCd, item.scateCd, item.lcateNm, item.mcateNm, item.scateNm)
        seen[key] = item
    return list(seen.values())
