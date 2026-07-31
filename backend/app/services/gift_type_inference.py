"""Small, deterministic guardrail for distinguishing products from activities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GiftTypeCode = Literal["product", "activity"]


# These are deliberately conservative clues rather than a second taxonomy. The
# model can add detail, but it must not override an obvious type signal.
ACTIVITY_HINTS: tuple[tuple[str, int], ...] = (
    ("露营看星星", 6),
    ("看星星", 5),
    ("观星", 5),
    ("星空", 4),
    ("露营", 4),
    ("陶艺体验", 6),
    ("烘焙体验", 6),
    ("手作体验", 5),
    ("密室逃脱", 5),
    ("剧本杀", 5),
    ("音乐会", 5),
    ("演唱会", 5),
    ("电影票", 5),
    ("门票", 5),
    ("课程", 4),
    ("工作坊", 5),
    ("体验", 3),
    ("预约", 3),
    ("演出", 4),
    ("展览", 4),
    ("采摘", 4),
    ("攀岩", 4),
    ("滑雪", 4),
    ("骑行", 4),
    ("徒步", 4),
    ("旅拍", 4),
    ("温泉", 4),
    ("按摩", 4),
    ("游乐园", 4),
    ("旅行", 3),
    ("旅游", 3),
    ("住宿", 3),
    ("餐厅", 3),
    ("下午茶", 3),
)

PRODUCT_HINTS: tuple[tuple[str, int], ...] = (
    ("礼盒", 4),
    ("冰箱贴", 5),
    ("书签", 5),
    ("徽章", 5),
    ("钥匙扣", 5),
    ("明信片", 5),
    ("笔记本", 5),
    ("保温杯", 5),
    ("水杯", 4),
    ("香薰", 4),
    ("帆布袋", 5),
    ("玩偶", 5),
    ("镜头", 5),
    ("帐篷", 5),
    ("睡袋", 5),
    ("底料", 4),
    ("茶叶", 4),
    ("零食", 4),
    ("巧克力", 4),
    ("香水", 4),
    ("口红", 4),
    ("衣服", 4),
    ("包包", 4),
    ("手链", 4),
    ("项链", 4),
    ("摆件", 4),
    ("文具", 4),
    ("护肤", 4),
    ("食品", 4),
    ("商品", 3),
    ("礼物", 2),
)

SHARED_PARTICIPATION_HINTS: tuple[tuple[str, int], ...] = (
    ("一起", 5),
    ("共同", 5),
    ("双人", 6),
    ("多人", 6),
    ("两人", 5),
    ("亲子", 5),
    ("情侣", 5),
    ("陪你", 5),
    ("陪他", 5),
    ("陪她", 5),
    ("带你", 5),
    ("和朋友", 5),
    ("和家人", 5),
    ("与朋友", 5),
    ("与家人", 5),
    ("我们", 4),
    ("相约", 5),
    ("约会", 5),
    ("邀请", 5),
    ("邀约", 5),
)

SINGLE_RECIPIENT_HINTS: tuple[tuple[str, int], ...] = (
    ("单人", 6),
    ("个人", 6),
    ("独享", 6),
    ("独自", 6),
    ("自己用", 6),
    ("个人使用", 6),
    ("个人健身卡", 7),
    ("单人spa", 7),
    ("单人潜水", 7),
    ("电子兑换码", 6),
    ("兑换码", 4),
    ("寄给", 4),
    ("邮寄", 4),
    ("快递", 4),
)


@dataclass(frozen=True)
class GiftTypeDecision:
    code: GiftTypeCode
    reason: str
    activity_clues: tuple[str, ...] = ()
    product_clues: tuple[str, ...] = ()
    shared_participation_clues: tuple[str, ...] = ()
    single_recipient_clues: tuple[str, ...] = ()


def infer_gift_type(text: str, selected_type: str) -> GiftTypeDecision:
    """Choose one type using shared participation as the only type boundary.

    Activity words alone are not enough: an experience can still be a Goods
    gift when only the recipient uses it. If participation is not stated, the
    collector's selection is respected and the reason asks for confirmation.
    """

    fallback: GiftTypeCode = "activity" if selected_type == "activity" else "product"
    normalized = " ".join(str(text or "").lower().split())
    activity_matches = tuple(
        clue for clue, _weight in ACTIVITY_HINTS if clue in normalized
    )
    product_matches = tuple(
        clue for clue, _weight in PRODUCT_HINTS if clue in normalized
    )
    shared_matches = tuple(
        clue for clue, _weight in SHARED_PARTICIPATION_HINTS if clue in normalized
    )
    single_matches = tuple(
        clue for clue, _weight in SINGLE_RECIPIENT_HINTS if clue in normalized
    )
    activity_score = sum(
        weight for clue, weight in ACTIVITY_HINTS if clue in normalized
    )
    product_score = sum(weight for clue, weight in PRODUCT_HINTS if clue in normalized)
    shared_score = sum(
        weight for clue, weight in SHARED_PARTICIPATION_HINTS if clue in normalized
    )
    single_score = sum(
        weight for clue, weight in SINGLE_RECIPIENT_HINTS if clue in normalized
    )

    if single_score > 0:
        chosen: GiftTypeCode = "product"
    elif shared_score > 0 and activity_score > 0 and activity_score >= product_score:
        chosen = "activity"
    elif product_score > 0:
        chosen = "product"
    elif fallback == "activity" and activity_score > 0:
        chosen = "activity"
    elif activity_score > 0:
        # A bare “露营/观星/演唱会” could be a solo voucher. Do not silently
        # turn it into a shared activity without evidence that the giver joins.
        chosen = "product"
    else:
        chosen = fallback

    if chosen == "activity":
        clue_text = "、".join(shared_matches[:4]) or "当前已选择的活动类型"
        reason = (
            f"识别到“{clue_text}”等共同参与线索；"
            "活动的核心是送礼人与收礼人共同投入时间并形成回忆，按活动处理。"
        )
    elif single_matches:
        clue_text = "、".join(single_matches[:4])
        reason = (
            f"识别到“{clue_text}”等收礼人独享线索；"
            "送礼人不需要出场，按商品处理，并生成拆箱、寄送或兑换提示。"
        )
    elif product_matches:
        clue_text = "、".join(product_matches[:4])
        reason = (
            f"识别到“{clue_text}”等商品线索；"
            "交付后由收礼人独享，按商品处理，并生成拆箱或定制贺卡方向。"
        )
    elif activity_matches:
        clue_text = "、".join(activity_matches[:4])
        reason = (
            f"识别到“{clue_text}”等活动场景，但还没有确认送礼人会共同参与；"
            "按商品暂归类。若送礼人会同行，请切换为活动。"
        )
    else:
        type_name = "活动" if chosen == "activity" else "商品"
        reason = (
            f"没有识别到足够明确的共同参与或独享线索，"
            f"沿用当前选择的“{type_name}”。"
        )

    return GiftTypeDecision(
        code=chosen,
        reason=reason,
        activity_clues=activity_matches,
        product_clues=product_matches,
        shared_participation_clues=shared_matches,
        single_recipient_clues=single_matches,
    )
