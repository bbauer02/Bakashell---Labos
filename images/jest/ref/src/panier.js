const { arrondir } = require('./prix');

class Panier {
  constructor() {
    this._lignes = [];
  }

  /** Ajoute un produit { ref, libelle, prixHT }. Une même référence est regroupée sur une seule ligne. */
  ajouter(produit, quantite = 1) {
    if (!Number.isInteger(quantite) || quantite <= 0) {
      throw new RangeError('Quantité invalide');
    }
    const ligne = this._lignes.find((l) => l.ref === produit.ref);
    if (ligne) {
      ligne.quantite += quantite;
    } else {
      this._lignes.push({ ref: produit.ref, libelle: produit.libelle, prixHT: produit.prixHT, quantite });
    }
    return this;
  }

  /** Retire complètement une référence du panier. */
  retirer(ref) {
    const avant = this._lignes.length;
    this._lignes = this._lignes.filter((l) => l.ref !== ref);
    if (this._lignes.length === avant) {
      throw new Error(`Produit ${ref} absent du panier`);
    }
    return this;
  }

  /** Copie des lignes : modifier le résultat ne doit pas modifier le panier. */
  lignes() {
    return this._lignes.map((l) => ({ ...l }));
  }

  nombreArticles() {
    return this._lignes.reduce((n, l) => n + l.quantite, 0);
  }

  totalHT() {
    return arrondir(this._lignes.reduce((t, l) => t + l.prixHT * l.quantite, 0));
  }

  estVide() {
    return this._lignes.length === 0;
  }
}

module.exports = { Panier };
