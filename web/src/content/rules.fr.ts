import type { RulesContent } from './rules'

// The app is in English for now: names shown on screen (slots, screens, orders, badges) stay
// in English here too, so the French rules match what the player sees.
export const rulesFr: RulesContent = {
  intro:
    'Une ligue privée de {min_players} à {max_players} amis, chacun contre tous. Les scores viennent des vrais cours de la Bourse, en Europe et aux États-Unis.',
  sections: [
    {
      id: 'campaign',
      title: 'La campagne',
      paragraphs: [
        'Une campagne dure {campaign_weeks_default} semaines par défaut (l’hôte peut choisir de {campaign_weeks_min} à {campaign_weeks_max}). Chaque semaine repart de 0 War Points (₩). Le vendredi soir, le classement de la semaine donne des points de campagne. Ils s’additionnent : celui qui en a le plus à la fin gagne.',
        'Les ex æquo se partagent les points de leurs places. À la fin, une égalité est départagée par le plus de victoires de semaine, puis le plus de War Points au total. La dernière semaine est le Final Assault : ses points de campagne comptent ×{final_week_multiplier}.',
      ],
    },
    {
      id: 'week',
      title: 'La semaine',
      paragraphs: [
        'Briefing (du vendredi soir au dimanche 23 h 59, heure de Paris) : choisissez votre escouade et, si vous voulez, jouez des ordres et proposez un pacte. Personne ne voit votre escouade avant le verrouillage. Si vous n’en avez enregistré aucune, une escouade est choisie pour vous.',
        'Segment 1 (du lundi au mercredi) : les marchés sont ouverts. Suivez votre score en direct sur le Front.',
        'Resupply (du mercredi soir au jeudi 8 h 59) : échangez une unité si vous voulez, et jouez des ordres. Vous décidez avant l’ouverture des marchés jeudi.',
        'Segment 2 (jeudi et vendredi) : les marchés à nouveau. Debrief (vendredi soir) : scores finaux, classement, exploits et badges.',
      ],
    },
    {
      id: 'squad',
      title: 'Votre escouade',
      paragraphs: [
        'Vous placez 5 actions, vos unités, dans 5 postes au front. Chaque poste multiplie les points de l’unité : Champion ×{slot_champion}, Veteran ×{slot_veteran}, Priority Target ×{slot_priority_target}, Marksman ×{slot_marksman}. Le Saboteur (×{slot_saboteur}) est un pari contre une action : il marque quand elle baisse et perd quand elle monte.',
        'Règles : au moins {front_min_per_region} unités européennes et {front_min_per_region} américaines au front. Le Champion et le Veteran viennent de régions différentes. Le Priority Target doit être l’une des {conflict_zone_size} actions de la Conflict Zone de la semaine : des actions dans l’actualité (résultats attendus, ou forte variation récente), signalées dans la liste.',
        'Vous gardez aussi {reserve_size} unités en réserve, dont au moins {reserve_min_per_region} européenne et {reserve_min_per_region} américaine. Au Resupply, vous pouvez faire {max_swaps} échange : une unité de réserve prend un poste du front pour jeudi et vendredi, et l’unité retirée garde ses points du lundi au mercredi. Après l’échange, le front doit toujours respecter les règles ci-dessus.',
        'Les fiches d’unités donnent des indices : la classe, d’Armored (calme) à Kamikaze (très agitée) ; le coefficient (« coef ») ; et la météo : On Fire ou Frozen (forte hausse ou forte baisse la semaine passée), Roller Coaster (gros écarts d’un jour à l’autre la semaine passée), Earnings this week (résultats attendus : gros mouvement possible).',
      ],
    },
    {
      id: 'scoring',
      title: 'Le score',
      paragraphs: [
        'Une action qui monte de 1 % rapporte {pf_per_percent} ₩ ; si elle baisse de 1 %, elle en coûte {pf_per_percent}, de l’ouverture du lundi à la clôture du vendredi. On multiplie ensuite par le poste et par le coefficient de l’unité. Une unité marque au maximum {unit_pf_clamp} ₩, en gain comme en perte.',
        'Le coefficient est affiché sur chaque unité : de ×{coef_min} pour les actions les plus agitées à ×{coef_max} pour les plus calmes. Une action calme qui monte un peu peut donc battre une action agitée qui monte beaucoup.',
        'Viennent ensuite bonus et pénalités : +{elite_unit_bonus} ₩ pour chaque unité du front qu’aucun autre joueur n’a dans son front (Elite unit) ; l’atout de votre commandant ; et les exploits : Total Victory +{feat_total_victory} ₩ (les 5 postes finissent en positif), Perfect Shot +{feat_perfect_shot} ₩ (vous avez la meilleure action de la semaine parmi les fronts de tous les joueurs, hors poste Saboteur), Resurrection +{feat_resurrection} ₩ (une action sous {resurrection_prev_max_return} % la semaine passée dépasse +{resurrection_this_min_return} % cette semaine).',
        'Attention : Heavy Losses coûte {feat_heavy_losses} ₩ pour chaque unité du front (hors Saboteur) dont l’action finit la semaine sous {heavy_losses_max_return} %, même si vous l’avez échangée. Les badges sont pour le plaisir : ils ne rapportent aucun War Point.',
      ],
    },
    {
      id: 'commanders',
      title: 'Les commandants',
      paragraphs: [
        'Chaque joueur choisit un commandant pour toute la campagne : un atout permanent, parfois avec une limite. Plusieurs joueurs peuvent choisir le même.',
      ],
    },
    {
      id: 'orders',
      title: 'Crédits et ordres',
      paragraphs: [
        'Les ordres sont facultatifs. Vous recevez {ammo_income} crédits par semaine et pouvez en garder jusqu’à {ammo_cap}. Dès la semaine 2, les joueurs de la moitié basse du classement de campagne en reçoivent {catch_up_ammo} de plus.',
        'Les crédits paient des attaques contre un rival, des défenses et des manœuvres sur votre escouade. Un ordre est payé quand il est joué et ne peut pas être annulé. Tactical Retreat, Field Promotion et Reversal se jouent chacun une fois par semaine au plus.',
        'Personne ne peut recevoir plus de {attack_cap_per_week} attaques par semaine (attaques bloquées comprises). Le premier seul de la campagne porte la Bounty : l’attaquer coûte {bounty_discount} crédit de moins, jamais moins de {min_order_cost}.',
      ],
    },
    {
      id: 'pacts',
      title: 'Les pactes',
      paragraphs: [
        'Au Briefing, vous pouvez proposer un pacte à un autre joueur (un pacte par semaine). S’il accepte, vous promettez tous les deux de ne pas vous attaquer cette semaine ; le pacte est public et ne peut pas être annulé. Attaquer quand même son allié fonctionne, mais c’est une trahison : {betrayal_penalty} ₩ (une fois par semaine) et le badge Traitor.',
      ],
    },
    {
      id: 'drone',
      title: 'Le Random Drone',
      paragraphs: [
        'Le Random Drone (actif sauf si l’hôte le retire) est un robot qui choisit une escouade au hasard chaque semaine. Son score est affiché, mais il ne prend ni rang ni points de campagne. Si vos unités seules (avant bonus et exploits) marquent moins que lui, vous recevez le badge Rusty.',
      ],
    },
  ],
  glossary: [
    { term: 'term.league', text: 'Une partie privée entre amis.' },
    { term: 'term.campaign', text: 'La partie entière, jouée sur plusieurs semaines.' },
    { term: 'term.squad', text: 'Vos 5 unités du front et votre réserve, pour une semaine.' },
    { term: 'term.unit', text: 'Une vraie action de votre escouade.' },
    { term: 'term.pf', text: 'War Points : votre score de la semaine. Il repart de 0 chaque semaine.' },
    { term: 'term.campaign_points', text: 'Les points donnés par votre rang du vendredi. Ils s’additionnent et désignent le vainqueur.' },
    { term: 'term.coefficient', text: 'Un multiplicateur propre à chaque unité : plus fort pour les actions calmes, plus faible pour les agitées.' },
    { term: 'term.segment', text: 'Le Segment 1 va du lundi au mercredi, le Segment 2 couvre jeudi et vendredi.' },
    { term: 'term.conflict_zone', text: 'Les actions dans l’actualité cette semaine. Seules elles peuvent être votre Priority Target.' },
    { term: 'term.ammo', text: 'Ce que vous dépensez pour jouer des ordres.' },
    { term: 'term.feat', text: 'Un bonus ou une pénalité en War Points pour un résultat particulier.' },
    { term: 'term.badge', text: 'Un titre de la semaine, pour le plaisir : aucun War Point.' },
    { term: 'term.bounty', text: 'Marque le premier de la campagne : moins cher à attaquer.' },
    { term: 'term.pact', text: 'Une promesse entre deux joueurs de ne pas s’attaquer cette semaine.' },
    { term: 'term.drone', text: 'Un robot avec une escouade au hasard, compté mais pas classé.' },
    { term: 'term.dispatch', text: 'Le petit journal de la ligue : lundi, jeudi et après le Debrief.' },
  ],
}
