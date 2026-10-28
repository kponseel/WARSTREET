import type { RulesContent } from './rules'

export const rulesFr: RulesContent = {
  intro:
    'Une ligue privée de {min_players} à {max_players} amis, chacun contre tous. Les vrais cours des actions européennes et américaines font les scores.',
  sections: [
    {
      id: 'campaign',
      title: 'La campagne',
      paragraphs: [
        'Une campagne dure de {campaign_weeks_min} à {campaign_weeks_max} semaines ({campaign_weeks_default} par défaut). Chaque semaine, les joueurs sont classés selon leurs War Points (₩) et le rang donne des points de campagne. Celui qui en a le plus à la fin gagne.',
        'La dernière semaine est l’Assaut final : ses points de campagne comptent ×{final_week_multiplier}.',
      ],
    },
    {
      id: 'week',
      title: 'La semaine',
      paragraphs: [
        'Briefing, du vendredi soir au dimanche 23 h 59 (heure de Paris) : composez votre escouade, jouez vos ordres de briefing, proposez des pactes.',
        'Segment 1, du lundi au mercredi : les marchés se battent, vous suivez le classement en direct.',
        'Ravitaillement, du mercredi soir au jeudi 8 h 59 : échangez des unités avec votre réserve et jouez vos ordres de ravitaillement.',
        'Segment 2, jeudi et vendredi, puis le Bilan de bataille le vendredi soir : scores finaux, classement, exploits, badges et Communiqué du Front.',
      ],
    },
    {
      id: 'squad',
      title: 'Votre escouade',
      paragraphs: [
        'Cinq unités au front, chacune une vraie action à un poste : Champion (×{slot_champion}), Vétéran (×{slot_veteran}), Tireur d’élite (×{slot_marksman}), Saboteur (×{slot_saboteur} : il marque quand son action baisse) et Cible prioritaire (×{slot_priority_target}), plus une réserve de {reserve_size}.',
        'Le front compte au moins {front_min_per_region} unités européennes et {front_min_per_region} américaines, le Vétéran vient de l’autre région que le Champion, et la Cible prioritaire fait partie des {conflict_zone_size} actions de la Zone de conflit de la semaine.',
        'Au ravitaillement, vous pouvez faire {max_swaps} échange : une unité de réserve remplace une unité du front pour le Segment 2.',
      ],
    },
    {
      id: 'scoring',
      title: 'Le score',
      paragraphs: [
        'Une unité marque sa performance de la semaine en % × {pf_per_percent} × le multiplicateur de son poste × son coefficient (les actions calmes ont un coefficient plus élevé), plafonné à ±{unit_pf_clamp} ₩ par poste.',
        'Bonus : +{elite_unit_bonus} ₩ pour chaque unité du front que personne d’autre n’a choisie, les exploits, et le passif de votre commandant.',
      ],
    },
    {
      id: 'commanders',
      title: 'Les commandants',
      paragraphs: [
        'Chaque joueur choisit un commandant pour toute la campagne. Chacun a un passif, et parfois une contrainte. Plusieurs joueurs peuvent choisir le même.',
      ],
    },
    {
      id: 'orders',
      title: 'Crédits et ordres',
      paragraphs: [
        'Vous recevez {ammo_income} crédits par semaine, jusqu’à {ammo_cap}. Ils paient les ordres : attaques (Frappe orbitale, Pillage, Blocus, Brouillage), défenses (Champ de force, Repli tactique) et manœuvres (Promotion sur le terrain, Retournement, Renseignement).',
        'Un joueur reçoit au plus {attack_cap_per_week} attaques par semaine. Le meneur de la campagne porte la Prime : l’attaquer coûte moins cher.',
      ],
    },
    {
      id: 'pacts',
      title: 'Les pactes',
      paragraphs: [
        'Pendant le briefing, deux joueurs peuvent signer un pacte de non-agression d’une semaine. Attaquer son allié est une trahison : {betrayal_penalty} ₩ et le badge Traître.',
      ],
    },
    {
      id: 'drone',
      title: 'Le Drone aléatoire',
      paragraphs: [
        'Un joueur fantôme compose une escouade au hasard chaque semaine. Il marque des points mais n’est jamais classé. Perdre contre lui vaut le badge Rouillé.',
      ],
    },
  ],
  glossary: [
    { term: 'term.league', text: 'Une partie privée entre amis.' },
    { term: 'term.campaign', text: 'La saison, faite de plusieurs semaines de marché.' },
    { term: 'term.squad', text: 'Vos cinq unités au front et votre réserve pour une semaine.' },
    { term: 'term.pf', text: 'War Points, le score de la semaine.' },
    { term: 'term.campaign_points', text: 'Points donnés par le rang de la semaine. Ils désignent le vainqueur.' },
    { term: 'term.conflict_zone', text: 'Les actions autorisées au poste de Cible prioritaire cette semaine.' },
    { term: 'term.ammo', text: 'La monnaie des ordres.' },
    { term: 'term.bounty', text: 'Marque le meneur de la campagne : moins cher à attaquer.' },
    { term: 'term.pact', text: 'Un accord de non-agression d’une semaine entre deux joueurs.' },
    { term: 'term.drone', text: 'Un joueur fantôme à l’escouade aléatoire, qui marque sans être classé.' },
    { term: 'term.dispatch', text: 'La gazette de la ligue, publiée le lundi, le jeudi et après le bilan.' },
  ],
}
