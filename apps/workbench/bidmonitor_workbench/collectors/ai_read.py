"""AI deep-read via local deerflow CLI: config, prompt, run, parse, hash."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DEFAULT_AI_SETTINGS = {
    "enabled": False,
    "deerflow_cli": "",
    "gateway": "http://127.0.0.1:8001",
    "timeout": 600,
    "recursion_limit": 300,
    "detail_len": 2000,
    "auto_enabled": False,
    "auto_limit": 10,
}


def load_ai_config(store):
    return DEFAULT_AI_SETTINGS | (store.setting('ai_read_settings') or {})


def locate_deerflow_cli(conf):
    explicit = (conf.get('deerflow_cli') or '').strip()
    if explicit:
        return explicit
    found = shutil.which('deerflowcli')
    if found:
        return found
    for candidate in (Path.home() / '.local' / 'bin', Path.home() / 'bin',
                      Path('/usr/local/bin'), Path('/opt/homebrew/bin')):
        path = candidate / 'deerflowcli'
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return ''


def build_prompt(project, conf):
    detail_len = int(conf.get('detail_len', 2000))
    fields = {
        '预算': project.get('budget', ''), '投标截止': project.get('deadline', ''),
        '采购人': project.get('purchaser', ''), '中标单位': project.get('win_company', ''),
        '中标金额': project.get('win_amount', ''),
    }
    field_lines = '\n'.join(f'{k}：{v}' for k, v in fields.items() if v)
    content = (project.get('content') or '')[:detail_len]
    return (
        f"精读招标公告，输出 JSON（采购单位/预算/投标截止/技术要点/业务关联度/跟进建议/风险提示），"
        f"附『建议文本』；可 web_fetch 核实。\n\n"
        f"标题：{project.get('title', '')}\n{field_lines}\n正文：{content}"
    )


def run_deerflow(task, conf):
    """Execute deerflowcli; return the produced report text or an error dict."""
    cli = locate_deerflow_cli(conf)
    if not cli:
        return {'error': '未配置 deerflow CLI 路径；请在设置页填写，或安装 deerflowcli 到 PATH'}
    out_dir = tempfile.mkdtemp(prefix='ai_read_')
    cmd = [cli, '--output-dir', out_dir, '--timeout', str(int(conf.get('timeout', 600))), '--no-stream']
    gateway = (conf.get('gateway') or '').strip()
    if gateway and gateway != 'http://127.0.0.1:8001':
        cmd += ['--gateway', gateway]
    recursion = int(conf.get('recursion_limit', 300))
    if recursion:
        cmd += ['--recursion-limit', str(recursion)]
    cmd.append(task)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=int(conf.get('timeout', 600)) + 60)
    except subprocess.TimeoutExpired:
        return {'error': 'AI 精读超时，请稍后重试'}
    except Exception as error:
        return {'error': f'deerflow 执行失败：{type(error).__name__}'}
    if proc.returncode != 0:
        text = (proc.stderr or proc.stdout or '')
        if re.search(r'(api[ -]?key|unauthorized|401|403|invalid[ _-]?credential)', text, re.I):
            return {'error': '模型凭据无效或已过期，请检查 deerflow Gateway 配置'}
        if re.search(r'(rate[ _-]?limit|429|quota|insufficient)', text, re.I):
            return {'error': '模型限流，请稍后重试'}
        if re.search(r'(connection|refused|timeout|unreachable|gateway)', text, re.I):
            return {'error': 'deerflow Gateway 不可达，请确认已启动（curl http://127.0.0.1:8001/health）'}
        return {'error': f'deerflow 退出码 {proc.returncode}'}
    hits = []
    for root, _, files in os.walk(out_dir):
        for fn in files:
            if fn.endswith('.md'):
                hits.append(Path(root) / fn)
    if not hits:
        return {'error': 'deerflow 未产出报告文件，请查看 deerflow 日志'}
    report = max(hits, key=os.path.getmtime).read_text(encoding='utf-8', errors='replace')
    return report


def parse_result(text):
    """Extract JSON from model output; degrade to an error dict on failure."""
    if not text:
        return {'error': 'AI 输出为空'}
    content = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.I)
    content = re.sub(r'\s*```$', '', content).strip()
    start, end = content.find('{'), content.rfind('}')
    if start < 0 or end <= start:
        return {'error': 'AI 输出解析失败', 'raw': text[:500]}
    try:
        return json.loads(content[start:end + 1])
    except ValueError:
        return {'error': 'AI 输出解析失败', 'raw': text[:500]}


def compute_hash(project, conf):
    detail_len = int(conf.get('detail_len', 2000))
    source = '|'.join([
        project.get('title', ''), project.get('budget', ''), project.get('deadline', ''),
        project.get('purchaser', ''), project.get('win_company', ''), project.get('win_amount', ''),
        (project.get('content') or '')[:detail_len],
    ])
    return hashlib.md5(source.encode('utf-8')).hexdigest()
