import type { RulesContent } from './rules'

export const rulesEn: RulesContent = {
  intro:
    'A private league of {min_players} to {max_players} friends, every player against every other one. Real EU and US stock prices drive the scores.',
  sections: [
    {
      id: 'campaign',
      title: 'The campaign',
      paragraphs: [
        'A campaign lasts {campaign_weeks_min} to {campaign_weeks_max} weeks ({campaign_weeks_default} by default). Each week, players are ranked by their Fantasy Points (FP) and the rank gives campaign points. The player with the most campaign points at the end wins.',
        'The last week is the Final Assault: its campaign points count ×{final_week_multiplier}.',
      ],
    },
    {
      id: 'week',
      title: 'The week',
      paragraphs: [
        'Briefing, from Friday night to Sunday 23:59 (Paris time): draft your squad, play briefing orders, propose pacts.',
        'Segment 1, Monday to Wednesday: the markets fight, you watch the live leaderboard.',
        'Resupply, from Wednesday evening to Thursday 08:59: swap units from your reserve and play resupply orders.',
        'Segment 2, Thursday and Friday, then the Debrief on Friday night: final scores, ranks, feats, badges and the Front Dispatch.',
      ],
    },
    {
      id: 'squad',
      title: 'Your squad',
      paragraphs: [
        'Five front units, each a real stock in a slot: Champion (×{slot_champion}), Veteran (×{slot_veteran}), Marksman (×{slot_marksman}), Saboteur (×{slot_saboteur}: it scores when its stock falls) and Priority Target (×{slot_priority_target}), plus a reserve of {reserve_size}.',
        'The front needs at least {front_min_per_region} EU and {front_min_per_region} US units, the Veteran comes from the other region than the Champion, and the Priority Target is one of the {conflict_zone_size} stocks of this week’s Conflict Zone.',
        'At resupply you may make {max_swaps} swap: a reserve unit replaces a front unit for Segment 2.',
      ],
    },
    {
      id: 'scoring',
      title: 'Scoring',
      paragraphs: [
        'A unit scores its weekly return in % × {pf_per_percent} × its slot multiplier × its coefficient (calmer stocks get a higher coefficient), capped at ±{unit_pf_clamp} FP per slot.',
        'Bonuses: +{elite_unit_bonus} FP for each front unit nobody else picked, feats, and your commander’s passive.',
      ],
    },
    {
      id: 'commanders',
      title: 'Commanders',
      paragraphs: [
        'Each player picks a commander for the whole campaign. Each has a passive ability, and sometimes a constraint. Several players may pick the same one.',
      ],
    },
    {
      id: 'orders',
      title: 'Ammo and orders',
      paragraphs: [
        'You get {ammo_income} ammo each week, up to {ammo_cap}. Spend it on orders: attacks (Orbital Strike, Plunder, Blockade, Jamming), defenses (Force Field, Tactical Retreat) and maneuvers (Field Promotion, Reversal, Intel).',
        'A player can receive at most {attack_cap_per_week} attacks per week. The campaign leader carries the Bounty: attacks against them are cheaper.',
      ],
    },
    {
      id: 'pacts',
      title: 'Pacts',
      paragraphs: [
        'During the briefing, two players can sign a one-week non-aggression pact. Attacking your ally is a betrayal: {betrayal_penalty} FP and the Traitor badge.',
      ],
    },
    {
      id: 'drone',
      title: 'The Random Drone',
      paragraphs: [
        'A ghost player drafts a random squad every week. It is scored but never ranked. Losing to it earns the Rusty badge.',
      ],
    },
  ],
  glossary: [
    { term: 'term.league', text: 'A private game between friends.' },
    { term: 'term.campaign', text: 'The season, made of several market weeks.' },
    { term: 'term.squad', text: 'Your five front units and your reserve for one week.' },
    { term: 'term.pf', text: 'Fantasy Points, the weekly score.' },
    { term: 'term.campaign_points', text: 'Points given by the weekly rank. They decide the winner.' },
    { term: 'term.conflict_zone', text: 'The stocks allowed in the Priority Target slot this week.' },
    { term: 'term.ammo', text: 'The currency you spend on orders.' },
    { term: 'term.bounty', text: 'Marks the campaign leader: cheaper to attack.' },
    { term: 'term.pact', text: 'A one-week non-aggression agreement between two players.' },
    { term: 'term.drone', text: 'A ghost player with a random squad, scored but not ranked.' },
    { term: 'term.dispatch', text: 'The league gazette, published Monday, Thursday and after the debrief.' },
  ],
}
