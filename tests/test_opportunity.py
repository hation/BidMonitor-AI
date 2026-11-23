"""Opportunity rule engine: relevance tiers, intent leads, and deadline urgency."""
from datetime import date

from apps.workbench.bidmonitor_workbench.collectors.opportunity import (
    classify, match_keywords, body_core_leads, urgency, DEFAULT_KEYWORDS,
)

CONF = dict(core=['服务器', '算力', 'GPU', '大模型'],
            secondary=['信息化', '系统集成', '运维'],
            exclude=['复印纸', '物业', '食堂'])


def test_match_keywords_exclude_wins_first():
    assert match_keywords('食堂食材采购服务器托管', CONF['core'], CONF['secondary'], CONF['exclude']) == ''
    assert match_keywords('复印纸采购项目', CONF['core'], CONF['secondary'], CONF['exclude']) == ''


def test_match_keywords_core_is_direct():
    assert match_keywords('政务云服务器采购项目', CONF['core'], CONF['secondary'], CONF['exclude']) == 'direct'
    assert match_keywords('算力中心建设项目', CONF['core'], CONF['secondary'], CONF['exclude']) == 'direct'


def test_match_keywords_secondary_is_related():
    assert match_keywords('校园信息化建设', CONF['core'], CONF['secondary'], CONF['exclude']) == 'related'
    assert match_keywords('机房运维服务采购', CONF['core'], CONF['secondary'], CONF['exclude']) == 'related'


def test_match_keywords_no_hit():
    assert match_keywords('市政道路改造工程', CONF['core'], CONF['secondary'], CONF['exclude']) == ''


def test_body_core_leads_three_distinct_cores():
    content = '本项目建设服务器集群，配套算力调度与GPU加速，部署大模型推理。'
    assert body_core_leads(content, CONF['core'], CONF['exclude']) == 'leads'


def test_body_core_leads_fails_with_too_few_cores():
    assert body_core_leads('本项目建设服务器集群。', CONF['core'], CONF['exclude']) == ''


def test_body_core_leads_ignored_when_excluded():
    content = '物业保洁服务，服务器机房日常维护，食堂后勤保障，GPU采购询价。'
    assert body_core_leads(content, CONF['core'], CONF['exclude']) == ''


def test_urgency_unknown_when_no_deadline():
    level, days = urgency('', date(2026, 12, 1))
    assert level == 'unknown' and days is None


def test_urgency_tiers():
    today = date(2026, 11, 23)
    assert urgency('2026-11-20', today) == ('expired', -3)
    assert urgency('2026-11-30', today) == ('urgent', 7)
    assert urgency('2026-12-06', today) == ('prep', 13)
    assert urgency('2026-12-20', today) == ('relaxed', 27)


def test_classify_combines():
    result = classify('政务云服务器采购项目', '正文', '2026-11-30', CONF, date(2026, 11, 23))
    assert result['relevance'] == 'direct'
    assert result['urgency_level'] == 'urgent'
    assert result['days_left'] == 7
    lead = classify('市政道路改造工程', '本项目建设服务器集群，配套算力调度与GPU加速，部署大模型推理。', '', CONF, date(2026, 11, 23))
    assert lead['relevance'] == 'leads'
    assert lead['urgency_level'] == 'unknown'


def test_default_keywords_have_three_tiers():
    assert DEFAULT_KEYWORDS['core'] and DEFAULT_KEYWORDS['secondary'] and DEFAULT_KEYWORDS['exclude']
