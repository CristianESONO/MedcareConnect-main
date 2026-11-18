import { useState } from 'react';

export function ContactPage() {
  const [mailNotice, setMailNotice] = useState('');

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const subject = `Contact MedCare - ${formData.get('type')}`;
    const body = [
      `Nom : ${formData.get('name')}`,
      `Email : ${formData.get('email')}`,
      `Profil : ${formData.get('type')}`,
      '',
      String(formData.get('message') ?? ''),
    ].join('\n');

    window.location.href = `mailto:contact@medcare.sn?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    setMailNotice("Votre application de messagerie va s'ouvrir avec le message prérempli. Envoyez-le depuis cette application pour nous contacter.");
  };

  return (
    <div className="mc-page-wrap">
      <header className="mc-page-hero">
        <div className="mc-container">
          <h1>Parlons de votre santé.</h1>
          <p>Une question ? Un partenariat ? Notre équipe est à votre écoute pour vous accompagner.</p>
        </div>
      </header>

      <section className="mc-section">
        <div className="mc-container">
          <div className="mc-contact-grid">
            <div className="mc-contact-info">
              <h2>Nous sommes à votre <em>écoute</em></h2>
              <p className="mc-section-lead" style={{ marginBottom: 48 }}>
                Que vous soyez un patient ayant besoin d'aide pour une recherche ou un professionnel souhaitant rejoindre notre réseau, n'hésitez pas à nous contacter.
              </p>

              <div className="mc-contact-item">
                <div className="mc-contact-icon"><i className="ti ti-mail" aria-hidden="true" /></div>
                <div className="mc-contact-text">
                  <h4>Email de support</h4>
                  <p><a href="mailto:contact@medcare.sn">contact@medcare.sn</a></p>
                  <p>Réponse sous 24h ouvrées.</p>
                </div>
              </div>
              <div className="mc-contact-item">
                <div className="mc-contact-icon"><i className="ti ti-brand-whatsapp" aria-hidden="true" /></div>
                <div className="mc-contact-text">
                  <h4>WhatsApp Direct</h4>
                  <p><a href="https://wa.me/221781673189" target="_blank" rel="noreferrer">+221 78 167 31 89</a></p>
                  <p>Disponible du lundi au samedi.</p>
                </div>
              </div>
              <div className="mc-contact-item">
                <div className="mc-contact-icon"><i className="ti ti-map-pin" aria-hidden="true" /></div>
                <div className="mc-contact-text">
                  <h4>Siège social</h4>
                  <p>Point E, Dakar</p>
                  <p>Sénégal</p>
                </div>
              </div>
            </div>

            <div className="mc-contact-form-card">
              <form onSubmit={handleSubmit}>
                <div className="mc-form-group">
                  <label className="mc-form-label" htmlFor="contact-name">Nom complet</label>
                  <input
                    type="text"
                    id="contact-name"
                    name="name"
                    className="mc-form-input"
                    placeholder="Ex: Moussa Diop"
                    autoComplete="name"
                    required
                  />
                </div>
                <div className="mc-form-group">
                  <label className="mc-form-label" htmlFor="contact-email">Adresse Email</label>
                  <input
                    type="email"
                    id="contact-email"
                    name="email"
                    className="mc-form-input"
                    placeholder="votre@email.com"
                    autoComplete="email"
                    required
                  />
                </div>
                <div className="mc-form-group">
                  <label className="mc-form-label" htmlFor="contact-type">Vous êtes</label>
                  <select id="contact-type" name="type" className="mc-form-input" defaultValue="Un Patient">
                    <option>Un Patient</option>
                    <option>Un Professionnel de santé</option>
                    <option>Un Partenaire (Assurance...)</option>
                    <option>Autre</option>
                  </select>
                </div>
                <div className="mc-form-group">
                  <label className="mc-form-label" htmlFor="contact-message">Votre message</label>
                  <textarea
                    id="contact-message"
                    name="message"
                    className="mc-form-input"
                    rows={5}
                    placeholder="Comment pouvons-nous vous aider ?"
                    required
                  />
                </div>
                <button type="submit" className="mc-btn-primary mc-btn-primary--block">Envoyer le message →</button>
                {mailNotice && <p role="status" className="mc-form-note">{mailNotice}</p>}
              </form>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
