/**
 * MedCare - Tokenized Tag Input for Multi-Act Search
 * Transforme le champ de recherche #search-q en un conteneur de badges/tags pour la multi-sélection d'actes :
 * - Création et suppression de tags interactifs
 * - Synchronisation bidirectionnelle avec les cases à cocher desktop et piliers mobiles
 * - Suggestions et autocomplétion intelligente
 * - Soumission fluide AJAX ou standard
 */
(function initTokenizedTagInput() {
  'use strict';

  if (!document.body.classList.contains('sipn-prestations')) return;
  
  var cfg = window.SIPN_CONFIG || {};
  var urls = cfg.urls || {};
  var autocompleteUrl = urls.autocomplete || '/api/search/autocomplete/';

  var searchInput = document.getElementById('search-q');
  if (!searchInput) return;
  
  var isMobile = window.innerWidth < 640;
  var tokenContainer = document.createElement('div');
  tokenContainer.className = 'tokenized-input-container';
  var minH = isMobile ? '36px' : '44px';
  var padLeft = isMobile ? '32px' : '44px';
  tokenContainer.style.cssText = 'display:flex;flex-wrap:wrap;gap:4px;align-items:center;padding:2px 8px 2px ' + padLeft + ';border:none;background:transparent;min-height:' + minH + ';position:relative;width:100%;box-sizing:border-box;';
  
  var inputWrapper = searchInput.parentElement;
  if (inputWrapper) {
    var searchIcon = inputWrapper.querySelector('svg');
    if (searchIcon) {
      searchIcon.style.position = 'absolute';
      searchIcon.style.left = isMobile ? '10px' : '12px';
      searchIcon.style.top = '50%';
      searchIcon.style.transform = 'translateY(-50%)';
      searchIcon.style.zIndex = '1';
    }
    
    inputWrapper.insertBefore(tokenContainer, searchInput);
    tokenContainer.appendChild(searchInput);
    if (searchIcon) tokenContainer.appendChild(searchIcon);
    var fontSz = isMobile ? '16px' : '14px';
    searchInput.style.cssText = 'flex:1 1 100px;min-width:100px;border:none;outline:none;padding:2px 4px;margin:0;font-size:' + fontSz + ';background:transparent;';
  }
  
  var autocompleteDropdown = document.createElement('div');
  autocompleteDropdown.className = 'autocomplete-dropdown';
  autocompleteDropdown.style.cssText = 'position:absolute;top:100%;left:0;right:0;background:#fff;border:1px solid #e5e7eb;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);max-height:200px;overflow-y:auto;z-index:100;display:none;margin-top:4px;';
  tokenContainer.appendChild(autocompleteDropdown);
  
  var tags = [];
  
  function createTag(text, value) {
    var tag = document.createElement('span');
    tag.className = 'token-tag';
    tag.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:4px 10px;background:#edfbfc;border:1px solid #a8e9f0;border-radius:20px;font-size:12px;font-weight:600;color:#0a5c8a;';
    tag.innerHTML = '<span>' + text + '</span><button type="button" class="token-remove" style="background:none;border:none;color:#0a5c8a;cursor:pointer;font-size:14px;padding:0;line-height:1;">&times;</button>';
    tag.dataset.value = value;
    
    tag.querySelector('.token-remove').addEventListener('click', function() {
      removeTag(tag);
    });
    
    return tag;
  }
  
  function addTag(text, value) {
    if (tags.some(function(t) { return t.dataset.value === value; })) return;
    
    var tag = createTag(text, value);
    tags.push(tag);
    tokenContainer.insertBefore(tag, searchInput);
    
    syncTagsWithCheckboxes();
    
    if (window._sipnAddSelectedActe) {
      window._sipnAddSelectedActe(value, text);
    }
  }
  
  function removeTag(tag) {
    var val = tag.dataset.value;
    var index = tags.indexOf(tag);
    if (index > -1) {
      tags.splice(index, 1);
      tag.remove();
      syncTagsWithCheckboxes();
      if (window._sipnRemoveSelectedActe) {
        window._sipnRemoveSelectedActe(val);
      }
    }
  }
  
  var defaultPlaceholder = searchInput.placeholder || 'Ex: NFS, Glycémie, IRM, Scanner…';

  function syncTagsWithCheckboxes() {
    var acteIds = tags.map(function(t) { return t.dataset.value; });

    if (tags.length > 0 && window.innerWidth >= 1024) {
      searchInput.placeholder = '';
    } else {
      searchInput.placeholder = defaultPlaceholder;
    }
    
    document.querySelectorAll('.dem-acte-row--multi').forEach(function(row) {
      var pk = row.getAttribute('data-dem-acte-pk');
      var isActive = acteIds.indexOf(pk) !== -1;
      row.classList.toggle('active', isActive);
      var chk = row.querySelector('.dem-acte-chk-box');
      if (chk) {
        chk.checked = isActive;
      }
    });
  }

  function normalizeStr(str) {
    return (str || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
  }

  function canonicalKey(str) {
    return (str || '').toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/\(.*?\)/g, '')
      .replace(/[^a-z0-9]+/g, '');
  }

  function findActeByName(name) {
    var normSearch = normalizeStr(name);
    if (!normSearch) return null;
    var acteRow = Array.from(document.querySelectorAll('.dem-acte-row--multi')).find(function(row) {
      var acteName = normalizeStr(row.getAttribute('data-dem-acte-name'));
      return acteName === normSearch || acteName.indexOf(normSearch) !== -1 || normSearch.indexOf(acteName) !== -1;
    });
    
    if (acteRow) {
      return {
        pk: acteRow.getAttribute('data-dem-acte-pk'),
        name: acteRow.getAttribute('data-dem-acte-name')
      };
    }

    if (window._sipnGetAllActeMap) {
      var allActes = window._sipnGetAllActeMap();
      for (var pk in allActes) {
        var aName = normalizeStr(allActes[pk]);
        if (aName === normSearch || aName.indexOf(normSearch) !== -1 || normSearch.indexOf(aName) !== -1) {
          return { pk: pk, name: allActes[pk] };
        }
      }
    }
    return null;
  }

  function processInputText(text) {
    if (!text) return;
    var parts = text.split(/[,;\n]/).map(function(s){ return s.trim(); }).filter(Boolean);
    parts.forEach(function(part) {
      if (!part) return;
      var matchingActe = findActeByName(part);
      if (matchingActe) {
        addTag(matchingActe.name, matchingActe.pk);
      }
    });
  }
  
  function triggerSearchUpdate() {
    var form = document.getElementById('search-form');
    if (!form) return;
    var searchBtns = document.querySelectorAll('.sipn-search-go');
    
    var rawVal = searchInput ? searchInput.value.trim() : '';

    function performSearch(resolvedActeId, resolvedActeName) {
      if (resolvedActeId && resolvedActeName) {
        addTag(resolvedActeName, String(resolvedActeId));
      }

      var acteIds = tags.map(function(t) { return t.dataset.value; }).filter(function(v){ return v && !v.startsWith('custom_'); });

      if (window._sipnGetSelectedIds) {
        var mobileIds = window._sipnGetSelectedIds();
        mobileIds.forEach(function(mid) {
          mid = String(mid);
          if (mid && acteIds.indexOf(mid) === -1) {
            acteIds.push(mid);
          }
        });
      }

      document.querySelectorAll('.dem-acte-row--multi.active').forEach(function(r) {
        var rpk = r.getAttribute('data-dem-acte-pk');
        if (rpk && acteIds.indexOf(rpk) === -1) {
          acteIds.push(rpk);
        }
      });

      form.querySelectorAll('input[name="acte"]').forEach(function(inp) {
        inp.remove();
      });

      acteIds.forEach(function(id) {
        var hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'acte';
        hidden.value = id;
        form.appendChild(hidden);
      });

      var qInput = form.querySelector('input[name="q"]');
      if (acteIds.length === 0 && rawVal) {
        if (!qInput) {
          qInput = document.createElement('input');
          qInput.type = 'hidden';
          qInput.name = 'q';
          form.appendChild(qInput);
        }
        qInput.value = rawVal;
      } else if (qInput && acteIds.length > 0) {
        qInput.value = '';
      }

      if (searchInput) {
        searchInput.value = '';
        var clearBtn = document.getElementById('btn-clear-q');
        if (clearBtn) clearBtn.style.display = 'none';
      }
      autocompleteDropdown.style.display = 'none';

      if (window.__tokenSearchDebounce) {
        clearTimeout(window.__tokenSearchDebounce);
      }
      window.__tokenSearchDebounce = setTimeout(function() {
        var u = new URL(form.action || window.location.href);
        var fd = new FormData(form);
        u.search = '';
        fd.forEach(function(v, k) {
          if (v !== '' && v != null) u.searchParams.append(k, v);
        });

        if (window.innerWidth < 1024) {
          u.hash = 'results-col';
          if (window._sipnGoResultsTab) {
            window._sipnGoResultsTab();
          }
        }

        if (typeof window.updatePageContent === 'function') {
          window.updatePageContent(u.toString());
          setTimeout(function() {
            searchBtns.forEach(function(btn){ btn.classList.remove('is-loading'); });
          }, 600);
        } else {
          window.location.assign(u.toString());
        }
      }, 120);
    }

    if (rawVal) {
      var localMatch = findActeByName(rawVal);
      if (localMatch) {
        performSearch(localMatch.pk, localMatch.name);
        return;
      }

      searchBtns.forEach(function(btn){ btn.classList.add('is-loading'); });
      fetch(autocompleteUrl + '?q=' + encodeURIComponent(rawVal))
        .then(function(r){ return r.json(); })
        .then(function(d){
          var sugs = (d.suggestions || []).filter(function(s){ return s.type === 'acte' && s.id; });
          if (sugs.length > 0) {
            var exact = sugs.find(function(s){ return normalizeStr(s.label) === normalizeStr(rawVal); });
            var chosen = exact || sugs[0];
            performSearch(chosen.id, chosen.label);
          } else {
            performSearch(null, null);
          }
        })
        .catch(function(){
          performSearch(null, null);
        });
    } else {
      performSearch(null, null);
    }
  }
  
  var clearBtn = document.getElementById('btn-clear-q');
  if (clearBtn) {
    clearBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
      }
      clearBtn.style.display = 'none';
      autocompleteDropdown.style.display = 'none';
    });
  }

  searchInput.addEventListener('input', function(e) {
    var text = searchInput.value.trim();
    var textNorm = normalizeStr(text);
    if (clearBtn) {
      clearBtn.style.display = text.length > 0 ? 'inline-flex' : 'none';
    }
    if (text.length < 2) {
      autocompleteDropdown.style.display = 'none';
      return;
    }
    
    var matches = [];
    var seenCanon = {};
    document.querySelectorAll('.dem-acte-row--multi').forEach(function(row) {
      var rawName = row.getAttribute('data-dem-acte-name') || '';
      var acteName = normalizeStr(rawName);
      var pk = row.getAttribute('data-dem-acte-pk');
      var cKey = canonicalKey(rawName);
      if (acteName.indexOf(textNorm) !== -1
          && !tags.some(function(t) { return t.dataset.value === pk; })
          && !seenCanon[cKey]) {
        seenCanon[cKey] = true;
        matches.push({ name: rawName, pk: pk });
      }
    });

    if (matches.length < 5 && window._sipnGetAllActeMap) {
      var allActes = window._sipnGetAllActeMap();
      Object.keys(allActes).forEach(function(pk) {
        if (matches.length >= 6) return;
        var rawName = allActes[pk];
        var acteName = normalizeStr(rawName);
        var cKey = canonicalKey(rawName);
        if (acteName.indexOf(textNorm) !== -1
            && !tags.some(function(t) { return t.dataset.value === pk; })
            && !matches.some(function(m) { return m.pk === pk; })
            && !seenCanon[cKey]) {
          seenCanon[cKey] = true;
          matches.push({ name: rawName, pk: pk });
        }
      });
    }

    if (matches.length === 0 && text.length >= 2) {
      fetch(autocompleteUrl + '?q=' + encodeURIComponent(text))
        .then(function(r){ return r.json(); })
        .then(function(d){
          var sugs = (d.suggestions || []).filter(function(s){ return s.type === 'acte' && s.id; });
          if (sugs.length > 0) {
            autocompleteDropdown.innerHTML = '';
            sugs.slice(0, 5).forEach(function(s) {
              var item = document.createElement('div');
              item.className = 'autocomplete-item';
              item.style.cssText = 'padding:11px 14px;min-height:46px;box-sizing:border-box;cursor:pointer;font-size:13px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;gap:8px;-webkit-tap-highlight-color:transparent;touch-action:manipulation;';
              item.innerHTML = '<span style="font-weight:600;color:#0d1b2a">' + s.label + '</span>' + (s.detail ? '<span style="font-size:11px;color:#9ca3af">' + s.detail + '</span>' : '');
              item.addEventListener('click', function() {
                addTag(s.label, String(s.id));
                searchInput.value = '';
                if (clearBtn) clearBtn.style.display = 'none';
                autocompleteDropdown.style.display = 'none';
                if (window.innerWidth >= 1024) {
                  triggerSearchUpdate();
                }
              });
              item.addEventListener('mouseenter', function() { item.style.background = '#f9fafb'; });
              item.addEventListener('mouseleave', function() { item.style.background = '#fff'; });
              autocompleteDropdown.appendChild(item);
            });
            autocompleteDropdown.style.display = 'block';
          }
        }).catch(function(){});
    }
    
    if (matches.length > 0) {
      autocompleteDropdown.innerHTML = '';
      matches.slice(0, 6).forEach(function(match) {
        var item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.style.cssText = 'padding:11px 14px;min-height:46px;box-sizing:border-box;cursor:pointer;font-size:13px;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;gap:8px;-webkit-tap-highlight-color:transparent;touch-action:manipulation;';
        item.innerHTML = '<span style="font-weight:600;color:#0d1b2a">' + match.name + '</span><span style="font-size:10.5px;color:#0a5c8a;background:#edfbfc;padding:3px 8px;border-radius:12px;font-weight:600;">+ Ajouter</span>';
        item.addEventListener('click', function() {
          addTag(match.name, match.pk);
          searchInput.value = '';
          if (clearBtn) clearBtn.style.display = 'none';
          autocompleteDropdown.style.display = 'none';
          if (window.innerWidth >= 1024) {
            triggerSearchUpdate();
          }
        });
        item.addEventListener('mouseenter', function() { item.style.background = '#f9fafb'; });
        item.addEventListener('mouseleave', function() { item.style.background = '#fff'; });
        autocompleteDropdown.appendChild(item);
      });
      autocompleteDropdown.style.display = 'block';
    }
  });
  
  searchInput.addEventListener('blur', function() {
    setTimeout(function() { autocompleteDropdown.style.display = 'none'; }, 220);
  });
  
  document.querySelectorAll('.sipn-search-go').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      triggerSearchUpdate();
    });
  });
  
  searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      triggerSearchUpdate();
    } else if (e.key === ',') {
      e.preventDefault();
      var val = searchInput.value;
      if (val) {
        processInputText(val);
        searchInput.value = '';
      }
    } else if (e.key === 'Backspace' && searchInput.value === '' && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  });

  var searchFormEl = document.getElementById('search-form');
  if (searchFormEl) {
    searchFormEl.addEventListener('submit', function(e) {
      e.preventDefault();
      triggerSearchUpdate();
    });
  }
  
  document.addEventListener('click', function(e) {
    var row = e.target.closest('.dem-acte-row--multi');
    if (row) {
      var pk = row.getAttribute('data-dem-acte-pk');
      var name = row.getAttribute('data-dem-acte-name');
      var isActive = row.classList.contains('active');
      
      if (isActive) {
        addTag(name, pk);
      } else {
        var tagToRemove = tags.find(function(t) { return t.dataset.value === pk; });
        if (tagToRemove) removeTag(tagToRemove);
      }
    }
  });
  
  function initFromUrl() {
    var urlParams = new URLSearchParams(window.location.search);
    var acteIds = urlParams.getAll('acte');
    if (searchFormEl) {
      searchFormEl.querySelectorAll('input[name="acte"]').forEach(function(inp) {
        if (inp.value && acteIds.indexOf(inp.value) === -1) {
          acteIds.push(inp.value);
        }
      });
    }
    
    acteIds.forEach(function(id) {
      var row = document.querySelector('.dem-acte-row--multi[data-dem-acte-pk="' + id + '"]');
      var name = '';
      if (row) {
        name = row.getAttribute('data-dem-acte-name') || row.innerText.trim();
      } else if (window._sipnGetActeName && window._sipnGetActeName(id)) {
        name = window._sipnGetActeName(id);
      } else {
        name = 'Acte #' + id;
      }
      addTag(name, id);
    });
  }
  
  setTimeout(initFromUrl, 300);
})();

