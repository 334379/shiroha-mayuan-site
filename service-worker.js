const CACHE_NAME = 'shiroha-quiz-pwa-20260614-3';

const APP_SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './app-icon.png',
  './styles.css',
  './question-bank.js',
  './question-bank.js?v=quiz-20260602',
  './app.js',
  './app.js?v=quiz-20260602-auto',
  './libs/README.txt',
  './libs/pdf.min.mjs',
  './libs/pdf.worker.min.mjs',
  './media/empty_state_no_question_bank.webp',
  './media/home_welcome_avatar.webp',
  './media/import_question_bank_folder.webp',
  './media/loading_waiting_hourglass.webp',
  './media/mascot_character_sheet.webp',
  './media/peeking.png',
  './media/peeking.webp',
  './media/quiz_in_progress_study.webp',
  './media/rest_sleep_pillow.webp',
  './media/splash_mascot.webp',
  './media/thinking_state_question.webp',
  './media/wrong_question_review_clipboard.webp',
  './data/banks-index.json',
  './data/mayuan-full.json',
  './data/mayuan-daolun.json',
  './data/mayuan-chapter1.json',
  './data/mayuan-chapter2.json',
  './data/mayuan-chapter3.json',
  './data/mayuan-chapter4.json',
  './data/mayuan-chapter5.json',
  './data/mayuan-chapter6.json',
  './data/mayuan-chapter7.json',
  './data/xsd-full.json',
  './data/xsd-chapter1.json',
  './data/xsd-chapter2.json',
  './data/xsd-chapter3.json',
  './data/xsd-chapter4.json',
  './data/xsd-chapter5.json',
  './data/xsd-chapter6.json',
  './data/xsd-chapter7.json',
  './data/xsd-chapter8.json',
  './data/xsd-chapter9.json',
  './data/xsd-chapter10.json',
  './data/xsd-chapter11.json',
  './data/xsd-chapter12.json',
  './data/xsd-chapter13.json',
  './data/xsd-chapter14.json',
  './data/xsd-chapter15.json',
  './data/xsd-chapter16.json',
  './data/xsd-chapter17.json',
  './data/xsd-chapter18.json'
];

self.addEventListener('install', function(event) {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(APP_SHELL);
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys()
      .then(function(keys) {
        return Promise.all(keys.filter(function(key) {
          return key !== CACHE_NAME;
        }).map(function(key) {
          return caches.delete(key);
        }));
      })
      .then(function() {
        return self.clients.claim();
      })
  );
});

self.addEventListener('fetch', function(event) {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(request).then(function(cached) {
      if (cached) return cached;
      return fetch(request).then(function(response) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(request, copy);
        });
        return response;
      }).catch(function() {
        return caches.match('./index.html');
      });
    })
  );
});
