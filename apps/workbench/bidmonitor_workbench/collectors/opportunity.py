"""Opportunity rule engine: relevance tiers and deadline urgency (pure functions)."""
from datetime import date, datetime


DEFAULT_KEYWORDS = {
    "core": ["服务器", "算力", "GPU", "人工智能", "大模型", "AI", "智算", "数据中心",
             "超算", "云服务", "云计算", "信创", "国产化", "整机", "存储", "机房",
             "政务大模型", "智能算力", "GPU服务器", "AI平台", "机器学习", "深度学习"],
    "secondary": ["信息化", "信息系统", "系统集成", "软件开发", "网络安全", "数据库",
                  "智慧", "终端设备", "数智", "运维服务", "数字化", "弱电", "网络设备",
                  "计算机", "办公设备", "显示器", "工作站"],
    "exclude": ["复印纸", "印刷服务", "会议服务", "车辆维修", "保洁", "物业", "食堂",
                "保险", "劳务", "餐饮", "绿化养护", "工程造价", "监理", "设计服务"],
}


def match_keywords(title, core, secondary, exclude):
    """Title scoring: exclude wins; core -> direct; secondary -> related; else ''."""
    if any(word in title for word in exclude):
        return ''
    if any(word in title for word in core):
        return 'direct'
    if any(word in title for word in secondary):
        return 'related'
    return ''


def body_core_leads(content, core, exclude, limit=4000):
    """Intent lead from the body when the title carried no signal."""
    body = (content or '')[:limit]
    core_hits = {word for word in core if word and word in body}
    exclude_hits = sum(1 for word in exclude if word and word in body)
    if len(core_hits) >= 3 and exclude_hits < 2:
        return 'leads'
    return ''


def urgency(deadline, today):
    """Deadline urgency tiers: expired / urgent / prep / relaxed / unknown."""
    if not deadline:
        return ('unknown', None)
    try:
        cutoff = datetime.fromisoformat(str(deadline)).date()
    except ValueError:
        return ('unknown', None)
    days = (cutoff - today).days
    if days <= 0:
        return ('expired', days)
    if days <= 7:
        return ('urgent', days)
    if days <= 14:
        return ('prep', days)
    return ('relaxed', days)


def classify(title, content, deadline, conf, today):
    """Combine title + body relevance and deadline urgency."""
    core = conf.get('core', [])
    secondary = conf.get('secondary', [])
    exclude = conf.get('exclude', [])
    relevance = match_keywords(title, core, secondary, exclude)
    if not relevance:
        relevance = body_core_leads(content, core, exclude)
    level, days = urgency(deadline, today)
    return {'relevance': relevance, 'urgency_level': level, 'days_left': days}
