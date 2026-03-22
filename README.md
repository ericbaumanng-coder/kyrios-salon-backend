# Kyrios Salon - Backend API

Backend FastAPI pour le site e-commerce et système de réservation Kyrios Salon.

## Fonctionnalités
- API E-commerce (produits, panier, commandes)
- Système de réservation avec dépôt Stripe
- CMS Admin complet
- Notifications (emails + WhatsApp) en mode démo
- Rappels automatiques 24h (APScheduler)

## Variables d'environnement requises

```env
MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net/
DB_NAME=kyrios_salon
CORS_ORIGINS=https://kyrios-salon.ch
STRIPE_API_KEY=sk_live_xxx
```

## Démarrage local

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```
