/**
 * Devis d'une commande de la boutique Cimes & Sentiers.
 *
 * Règles du service commercial (conditions générales de vente) :
 *  1. Prix unitaire TTC = prix HT + 20 % de TVA, arrondi au centime.
 *  2. Une ligne vaut prix unitaire TTC × quantité.
 *  3. Remise par quantité : une ligne d'au moins {{QTE}} exemplaires d'un même article bénéficie de
 *     {{TAUX}} % de remise sur CETTE ligne (montant de la remise arrondi au centime).
 *     Les autres lignes de la commande ne changent pas.
 *  4. Frais de port : {{FRAIS_FR}} €, offerts quand le montant des produits, remises déduites,
 *     atteint {{SEUIL}} € TTC (seuil compris).
 *  5. Total = produits (remises déduites) + frais de port.
 */
'use strict';

const TVA = 0.2;
const QUANTITE_REMISE = {{QTE}};
const TAUX_REMISE = {{TAUX}};
const FRAIS_PORT = {{FRAIS}};
const SEUIL_PORT_OFFERT = {{SEUIL}};

/** Arrondi au centime (le passage par toFixed corrige les erreurs de représentation : 1,005 donne 1,01). */
function arrondi(montant) {
  return Math.round(Number((montant * 100).toFixed(6))) / 100;
}

function prixUnitaireTTC(prixHT) {
  return arrondi(prixHT * (1 + TVA));
}

function ligneDevis(article, quantite, remiseAccordee) {
  const brut = arrondi(prixUnitaireTTC(article.prixHT) * quantite);
  const remise = remiseAccordee ? arrondi((brut * TAUX_REMISE) / 100) : 0;
  return { ref: article.ref, quantite, brut, remise, net: arrondi(brut - remise) };
}

/**
 * lignes : [{ ref, quantite }] ; catalogue : [{ ref, prixHT }].
 * Renvoie { lignes, brut, remises, produits, port, total } (montants TTC en euros).
 */
function calculerDevis(lignes, catalogue) {
  if (!Array.isArray(lignes) || lignes.length === 0) throw new Error('Le devis ne contient aucun article');
  const details = lignes.map(({ ref, quantite }) => {
    const article = catalogue.find((p) => p.ref === ref);
    if (!article) throw new Error(`Article inconnu : ${ref}`);
    if (!Number.isInteger(quantite) || quantite < 1) throw new Error(`Quantité invalide pour ${ref} : ${quantite}`);
    return ligneDevis(article, quantite, quantite >= QUANTITE_REMISE);
  });
  const brut = arrondi(details.reduce((somme, l) => somme + l.brut, 0));
  const remises = arrondi(details.reduce((somme, l) => somme + l.remise, 0));
  const produits = arrondi(brut - remises);
  const port = produits >= SEUIL_PORT_OFFERT ? 0 : FRAIS_PORT;
  return { lignes: details, brut, remises, produits, port, total: arrondi(produits + port) };
}

module.exports = { prixUnitaireTTC, calculerDevis };
