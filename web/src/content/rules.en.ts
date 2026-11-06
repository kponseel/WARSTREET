import type { RulesContent } from './rules'

// Names shown on screen (slots, screens, orders, badges) are written as the app shows them.
export const rulesEn: RulesContent = {
  intro:
    'A private league of {min_players} to {max_players} friends, everyone against everyone. Scores come from real stock prices in Europe and the United States.',
  sections: [
    {
      id: 'campaign',
      title: 'The campaign',
      paragraphs: [
        'A campaign lasts {campaign_weeks_default} weeks by default (the host can pick {campaign_weeks_min} to {campaign_weeks_max}). Every week starts again at 0 War Points (₩). On Friday night, the week’s ranking gives campaign points. Campaign points add up: the most at the end wins.',
        'Tied players share the points of their places. At the end, a tie is broken by the most weekly wins, then the most War Points in total. The last week is the Final Assault: its campaign points count ×{final_week_multiplier}.',
      ],
    },
    {
      id: 'week',
      title: 'The week',
      paragraphs: [
        'Briefing (Friday night to Sunday 23:59, Paris time): pick your squad and, if you like, play orders and offer a pact. Nobody sees your squad before the lock. If you saved none, one is picked for you.',
        'Segment 1 (Monday to Wednesday): the markets are open. Follow your live score on the Front.',
        'Resupply (Wednesday evening to Thursday 08:59): swap a unit if you want, and play orders. You decide before Thursday’s markets open.',
        'Segment 2 (Thursday and Friday): the markets again. Debrief (Friday night): final scores, ranking, feats and badges.',
      ],
    },
    {
      id: 'squad',
      title: 'Your squad',
      paragraphs: [
        'You place 5 stocks, your units, in 5 front slots. Each slot multiplies the unit’s points: Champion ×{slot_champion}, Veteran ×{slot_veteran}, Priority Target ×{slot_priority_target}, Marksman ×{slot_marksman}. The Saboteur (×{slot_saboteur}) is a bet against a stock: it scores when the stock falls and loses when it rises.',
        'Squad rules: at least {front_min_per_region} European and {front_min_per_region} American units in the front. The Champion and the Veteran come from different regions. The Priority Target must be one of this week’s {conflict_zone_size} Conflict Zone stocks: stocks in the news (results due, or big recent moves), tagged in the list.',
        'You also keep {reserve_size} units in reserve, with at least {reserve_min_per_region} European and {reserve_min_per_region} American. At Resupply you may make {max_swaps} swap: a reserve unit takes a front slot for Thursday and Friday, and the unit taken out keeps its Monday to Wednesday points. After the swap, the front must still follow the rules above.',
        'Unit cards give hints: the class, from Armored (calm) to Kamikaze (wild); the coefficient (“coef”); and the weather: On Fire or Frozen (big rise or fall last week), Roller Coaster (big daily swings last week), Earnings this week (results due, so a big move is possible).',
      ],
    },
    {
      id: 'scoring',
      title: 'Scoring',
      paragraphs: [
        'A stock that rises 1 % earns {pf_per_percent} ₩; one that falls 1 % costs {pf_per_percent} ₩, from Monday’s opening price to Friday’s closing price. This is multiplied by the slot and by the unit’s coefficient. A unit scores at most {unit_pf_clamp} ₩, up or down.',
        'The coefficient is shown on each unit: from ×{coef_min} for the wildest stocks to ×{coef_max} for the calmest. A calm stock that rises a little can beat a wild one that rises a lot.',
        'Then come bonuses and penalties: +{elite_unit_bonus} ₩ for each front unit that no other player has in their front (Elite unit); your commander’s bonus; and the feats: Total Victory +{feat_total_victory} ₩ (all 5 slots end positive), Perfect Shot +{feat_perfect_shot} ₩ (you hold the week’s best stock of all players’ fronts, outside the Saboteur slot), Resurrection +{feat_resurrection} ₩ (a stock below {resurrection_prev_max_return} % last week rises above +{resurrection_this_min_return} % this week).',
        'Careful: Heavy Losses costs {feat_heavy_losses} ₩ for each front unit (except the Saboteur) whose stock ends the week below {heavy_losses_max_return} %, even if you swapped it out. Badges are just for fun: they give no War Points.',
      ],
    },
    {
      id: 'commanders',
      title: 'Commanders',
      paragraphs: [
        'Each player picks a commander for the whole campaign: a bonus that always applies, sometimes with a limit. Several players may pick the same one.',
      ],
    },
    {
      id: 'orders',
      title: 'Credits and orders',
      paragraphs: [
        'Orders are optional. You get {ammo_income} credits each week and can save up to {ammo_cap}. From week 2, players in the bottom half of the campaign standings get +{catch_up_ammo} more.',
        'Credits pay for attacks on a rival, defenses, and moves on your own squad. An order is paid when played and cannot be cancelled. Tactical Retreat, Field Promotion and Reversal can each be played once per week.',
        'Nobody can receive more than {attack_cap_per_week} attacks a week (blocked ones count). The sole campaign leader carries the Bounty: attacking them costs {bounty_discount} credit less, never below {min_order_cost}.',
      ],
    },
    {
      id: 'pacts',
      title: 'Pacts',
      paragraphs: [
        'At the Briefing you can offer a pact to another player (one pact per week). If they accept, you both promise not to attack each other this week; the pact is public and cannot be cancelled. Attacking your ally anyway still works, but it is a betrayal: {betrayal_penalty} ₩ (once per week) and the Traitor badge.',
      ],
    },
    {
      id: 'drone',
      title: 'The Random Drone',
      paragraphs: [
        'The Random Drone (on unless the host turns it off) is a robot that picks a random squad every week. Its score is shown, but it takes no rank and no campaign points. If your units alone (before bonuses and feats) score less than it, you get the Rusty badge.',
      ],
    },
  ],
  glossary: [
    { term: 'term.league', text: 'A private game between friends.' },
    { term: 'term.campaign', text: 'The whole game, played over several weeks.' },
    { term: 'term.squad', text: 'Your 5 front units and your reserve, for one week.' },
    { term: 'term.unit', text: 'A real stock in your squad.' },
    { term: 'term.pf', text: 'War Points: your score for the week. Back to 0 every week.' },
    { term: 'term.campaign_points', text: 'Points given by your Friday rank. They add up and decide the winner.' },
    { term: 'term.coefficient', text: 'A multiplier on each unit: higher for calm stocks, lower for wild ones.' },
    { term: 'term.segment', text: 'Segment 1 is Monday to Wednesday, Segment 2 is Thursday and Friday.' },
    { term: 'term.conflict_zone', text: 'This week’s stocks in the news. Only they can be your Priority Target.' },
    { term: 'term.ammo', text: 'What you spend on orders.' },
    { term: 'term.feat', text: 'A bonus or a penalty in War Points for a special result.' },
    { term: 'term.badge', text: 'A title for the week, just for fun: no War Points.' },
    { term: 'term.bounty', text: 'Marks the campaign leader: cheaper to attack.' },
    { term: 'term.pact', text: 'A promise between two players not to attack each other this week.' },
    { term: 'term.drone', text: 'A robot with a random squad, scored but not ranked.' },
    { term: 'term.dispatch', text: 'The league’s little newspaper: Monday, Thursday and after the Debrief.' },
  ],
}
