"""
Monitored players for Taraji AI - current squad members on departure watch
plus reported transfer targets. Backed by config/players.json; that file is
the one to edit when the mercato moves.

Stdlib-only on purpose: utils imports config, so importing utils from here
would create an import cycle.
"""
import json
from pathlib import Path
from typing import Dict, List

PLAYERS_PATH = Path(__file__).parent / "players.json"


def load_players() -> Dict[str, List[Dict]]:
    """Return {'targets': [...], 'squad': [...]} from players.json.

    A missing or malformed file raises - player monitoring silently
    disappearing is worse than a visibly failed run.
    """
    with open(PLAYERS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {
        'targets': data.get('targets', []),
        'squad': data.get('squad', []),
    }


def all_players() -> List[Dict]:
    """Targets and squad players as one flat list."""
    data = load_players()
    return data['targets'] + data['squad']


def match_variants(player: Dict) -> List[str]:
    """Every name spelling of a player usable for keyword matching."""
    variants = [player['name']]
    if player.get('name_ar'):
        variants.append(player['name_ar'])
    variants.extend(player.get('aliases', []))
    return variants
