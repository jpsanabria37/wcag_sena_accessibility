// axe-core-setup.js
const { configureAxe, run } = require('axe-core');

const axe = configureAxe({
  locale: 'es' // Establecer el idioma a español
});

module.exports = axe.run;
