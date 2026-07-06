from __future__ import annotations

from replay.mcap.schemas import SceneSpec

# cluster_01 default poses for H2-grasp orange-to-bowl task
H2_GRASP_ORANGE = (0.32, 0.08, 0.79)
H2_GRASP_BOWL = (0.28, 0.12, 0.755)


def get_scene(scene_id: str, object_class: str) -> SceneSpec:
    if scene_id == "H2-grasp" or object_class == "orange":
        return SceneSpec(
            scene_id="H2-grasp",
            object_class=object_class,
            table_height_m=0.75,
            orange_pos=H2_GRASP_ORANGE,
            bowl_pos=H2_GRASP_BOWL,
            orange_radius_m=0.035,
            bowl_radius_m=0.06,
        )
    return SceneSpec(scene_id=scene_id, object_class=object_class)
