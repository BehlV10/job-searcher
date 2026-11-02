/**
 * StaffHunt - Frontend Application Logic
 * Multi-board search, granular seniority (Senior, Staff, Senior Staff, Principal),
 * ML/AI vs General SWE separation, recruiter direct profiles & hiring posts.
 */

(function () {
  'use strict';

  // Application State
  const state = {
    jobs: [],
    companies: [],
    filteredJobs: [],
    filteredCompanies: [],
    metadata: {},
    activeTab: 'jobs',
    userProfile: {
      name: "Varun Behl",
      target_roles: ["Staff Software Engineer", "Senior Software Engineer", "Senior Staff Software Engineer", "Principal Software Engineer"],
      target_locations: ["New York, NY", "Boston, MA"],
      min_salary: 180000,
      outreach_template: "Hi {{recruiter_name}},\n\nI noticed {{company}} is hiring for a {{job_title}} in {{location}}. With extensive experience architecting high-scale distributed systems and leading engineering initiatives, I'm very excited about {{company}}'s mission.\n\nI've attached my resume and would love to connect for a quick 10-minute chat if you're open to it.\n\nBest regards,\n{{user_name}}"
    },
    savedJobIds: new Set(JSON.parse(localStorage.getItem('staffhunt_saved') || '[]')),
    filters: {
      search: '',
      discipline: 'all', // 'all' | 'General Software' | 'Machine Learning / AI'
      archetype: 'all',
      location: 'all',
      seniority: 'all',  // 'all' | 'Senior' | 'Staff' | 'Senior Staff' | 'Principal' | 'Engineering Manager'
      minSalary: 180000,
      minYoE: 'all',
      source: 'all',
      sortBy: 'salary-desc'
    },
    companyFilters: {
      location: 'all',
      search: ''
    },
    selectedJob: null
  };

  // DOM Elements
  const el = {
    // Nav tabs
    navTabJobs: document.getElementById('nav-tab-jobs'),
    navTabCompanies: document.getElementById('nav-tab-companies'),
    mobileTabJobs: document.getElementById('mobile-tab-jobs'),
    mobileTabCompanies: document.getElementById('mobile-tab-companies'),
    viewJobListings: document.getElementById('view-job-listings'),
    viewCompanies: document.getElementById('view-companies'),
    badgeNavJobsCount: document.getElementById('badge-nav-jobs-count'),

    // Jobs View
    jobsContainer: document.getElementById('jobs-container'),
    emptyState: document.getElementById('empty-state'),
    searchInput: document.getElementById('search-input'),
    searchClear: document.getElementById('search-clear'),
    discButtons: document.querySelectorAll('.filter-disc-btn'),
    locButtons: document.querySelectorAll('.filter-loc-btn'),
    archetypeSelect: document.getElementById('filter-archetype'),
    senioritySelect: document.getElementById('filter-seniority'),
    salarySelect: document.getElementById('filter-salary'),
    yoeSelect: document.getElementById('filter-yoe'),
    sourceSelect: document.getElementById('filter-source'),
    sortSelect: document.getElementById('sort-by'),
    resetBtn: document.getElementById('btn-reset-filters'),
    emptyResetBtn: document.getElementById('btn-empty-reset'),
    showingCount: document.getElementById('showing-count'),
    salaryBadge: document.getElementById('salary-filter-badge'),
    metricTotal: document.getElementById('metric-total-jobs'),
    metricSalary: document.getElementById('metric-salary-jobs'),
    metricMl: document.getElementById('metric-ml-jobs'),
    metricStaff: document.getElementById('metric-staff-jobs'),
    countLocAll: document.getElementById('count-loc-all'),
    countLocNyc: document.getElementById('count-loc-nyc'),
    countLocBoston: document.getElementById('count-loc-boston'),
    countDiscAll: document.getElementById('count-disc-all'),
    countDiscSwe: document.getElementById('count-disc-swe'),
    countDiscMl: document.getElementById('count-disc-ml'),
    btnSaved: document.getElementById('btn-saved-jobs'),
    badgeSavedCount: document.getElementById('badge-saved-count'),
    themeToggle: document.getElementById('btn-theme-toggle'),

    // Companies View
    companiesGrid: document.getElementById('companies-grid'),
    companySearchInput: document.getElementById('company-search-input'),
    compLocButtons: document.querySelectorAll('.comp-filter-btn'),
    countCompAll: document.getElementById('count-comp-all'),
    countCompNyc: document.getElementById('count-comp-nyc'),
    countCompBoston: document.getElementById('count-comp-boston'),

    // Recruiter Modal
    recruiterModal: document.getElementById('recruiter-modal'),
    modalClose: document.getElementById('modal-close'),
    modalInitial: document.getElementById('modal-company-initial'),
    modalCompName: document.getElementById('modal-company-name'),
    modalJobTitle: document.getElementById('modal-job-title'),
    modalPocName: document.getElementById('modal-poc-name'),
    modalTeamName: document.getElementById('modal-team-name'),
    modalPartnerBadge: document.getElementById('modal-partner-badge'),
    modalBtnDirectProfile: document.getElementById('modal-btn-direct-profile'),
    modalBtnHiringPosts: document.getElementById('modal-btn-hiring-posts'),
    modalBtnRecruiter: document.getElementById('modal-btn-recruiter'),
    modalBtnManager: document.getElementById('modal-btn-manager'),
    modalOutreachText: document.getElementById('modal-outreach-text'),
    modalBtnCopy: document.getElementById('modal-btn-copy'),
    copyToast: document.getElementById('copy-toast'),

    // Drawer
    drawerBackdrop: document.getElementById('job-drawer-backdrop'),
    drawer: document.getElementById('job-drawer'),
    drawerClose: document.getElementById('drawer-close'),
    drawerCompany: document.getElementById('drawer-company'),
    drawerDiscipline: document.getElementById('drawer-discipline'),
    drawerSource: document.getElementById('drawer-source'),
    drawerTitle: document.getElementById('drawer-title'),
    drawerLocation: document.getElementById('drawer-location'),
    drawerDate: document.getElementById('drawer-date'),
    drawerSalary: document.getElementById('drawer-salary'),
    drawerExperience: document.getElementById('drawer-experience'),
    drawerTechStack: document.getElementById('drawer-tech-stack'),
    drawerRecruiterPoc: document.getElementById('drawer-recruiter-poc'),
    drawerBtnRecruiterProfile: document.getElementById('drawer-btn-recruiter-profile'),
    drawerDescription: document.getElementById('drawer-description'),
    drawerBtnApply: document.getElementById('drawer-btn-apply'),
    drawerBtnOutreach: document.getElementById('drawer-btn-outreach'),
    drawerBtnOutreachInline: document.getElementById('drawer-btn-outreach-inline'),

    // Profile Modal
    profileModal: document.getElementById('profile-modal'),
    btnOpenProfile: document.getElementById('btn-open-profile'),
    profileModalClose: document.getElementById('profile-modal-close'),
    prefUserName: document.getElementById('pref-user-name'),
    prefRoleTitle: document.getElementById('pref-role-title'),
    prefOutreachTemplate: document.getElementById('pref-outreach-template'),
    prefSaveBtn: document.getElementById('pref-save-btn'),

    // Saved Jobs Modal
    savedModal: document.getElementById('saved-modal'),
    savedModalClose: document.getElementById('saved-modal-close'),
    savedJobsList: document.getElementById('saved-jobs-list')
  };

  // Initialization
  async function init() {
    initTheme();
    loadProfile();
    bindEvents();
    await Promise.all([fetchJobs(), fetchCompanies()]);
  }

  function initTheme() {
    const isDark = localStorage.getItem('staffhunt_theme') === 'dark' ||
      (!('staffhunt_theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('staffhunt_theme', isDark ? 'dark' : 'light');
    if (window.lucide) lucide.createIcons();
  }

  function loadProfile() {
    const stored = localStorage.getItem('staffhunt_profile');
    if (stored) {
      try {
        state.userProfile = { ...state.userProfile, ...JSON.parse(stored) };
      } catch (e) {
        console.error("Error loading profile", e);
      }
    }
  }

  // Fetch Jobs
  async function fetchJobs() {
    try {
      const response = await fetch('jobs.json?t=' + Date.now());
      if (!response.ok) throw new Error('Failed to load jobs.json: ' + response.status);
      const data = await response.json();
      state.jobs = data.jobs || [];
      state.metadata = data.metadata || {};

      if (data.user_profile) {
        state.userProfile = { ...data.user_profile, ...state.userProfile };
      }

      updateTopMetrics();
      applyFilters();
    } catch (err) {
      console.error('Fetch jobs error:', err);
      el.jobsContainer.innerHTML = `
        <div class="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-2xl p-6 text-center text-red-800 dark:text-red-200">
          <p class="font-bold">Error loading jobs dataset</p>
          <p class="text-xs mt-1">Please ensure jobs.json is present in the web root or run python3 -m scraper.run_scraper.</p>
        </div>
      `;
    }
  }

  // Fetch Companies Directory
  async function fetchCompanies() {
    try {
      const response = await fetch('companies.json?t=' + Date.now());
      if (!response.ok) throw new Error('Failed to load companies.json');
      state.companies = await response.json();
      updateCompanyCounts();
      renderCompanies();
    } catch (err) {
      console.error('Fetch companies error:', err);
    }
  }

  function updateTopMetrics() {
    const total = state.jobs.length;
    const withSalary = state.jobs.filter(j => j.salary).length;
    const nyc = state.jobs.filter(j => j.city === 'New York, NY').length;
    const boston = state.jobs.filter(j => j.city === 'Boston, MA').length;

    const mlCount = state.jobs.filter(j => j.discipline === 'Machine Learning / AI').length;
    const sweCount = total - mlCount;
    const staffTierCount = state.jobs.filter(j => ['Staff', 'Senior Staff', 'Principal'].includes(j.seniority)).length;

    if (el.metricTotal) el.metricTotal.textContent = total;
    if (el.metricSalary) el.metricSalary.textContent = withSalary;
    if (el.metricMl) el.metricMl.textContent = mlCount;
    if (el.metricStaff) el.metricStaff.textContent = staffTierCount;

    if (el.countLocAll) el.countLocAll.textContent = total;
    if (el.countLocNyc) el.countLocNyc.textContent = nyc;
    if (el.countLocBoston) el.countLocBoston.textContent = boston;

    if (el.countDiscAll) el.countDiscAll.textContent = total;
    if (el.countDiscSwe) el.countDiscSwe.textContent = sweCount;
    if (el.countDiscMl) el.countDiscMl.textContent = mlCount;

    if (el.badgeNavJobsCount) el.badgeNavJobsCount.textContent = total;
    updateSavedBadge();
  }

  function updateSavedBadge() {
    if (el.badgeSavedCount) el.badgeSavedCount.textContent = state.savedJobIds.size;
  }

  function updateCompanyCounts() {
    const total = state.companies.length;
    const nyc = state.companies.filter(c => c.metro === 'New York, NY').length;
    const boston = state.companies.filter(c => c.metro === 'Boston, MA').length;

    if (el.countCompAll) el.countCompAll.textContent = total;
    if (el.countCompNyc) el.countCompNyc.textContent = nyc;
    if (el.countCompBoston) el.countCompBoston.textContent = boston;
  }

  // Tab switching
  function switchTab(tab) {
    state.activeTab = tab;
    if (tab === 'jobs') {
      el.viewJobListings.classList.remove('hidden');
      el.viewCompanies.classList.add('hidden');

      el.navTabJobs.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      el.navTabJobs.classList.remove('text-slate-600', 'dark:text-slate-400');
      el.navTabCompanies.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      el.navTabCompanies.classList.add('text-slate-600', 'dark:text-slate-400');

      if (el.mobileTabJobs) {
        el.mobileTabJobs.classList.add('bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        el.mobileTabCompanies.classList.remove('bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      }
    } else {
      el.viewJobListings.classList.add('hidden');
      el.viewCompanies.classList.remove('hidden');

      el.navTabCompanies.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      el.navTabCompanies.classList.remove('text-slate-600', 'dark:text-slate-400');
      el.navTabJobs.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      el.navTabJobs.classList.add('text-slate-600', 'dark:text-slate-400');

      if (el.mobileTabCompanies) {
        el.mobileTabCompanies.classList.add('bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        el.mobileTabJobs.classList.remove('bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
      }
      renderCompanies();
    }
    if (window.lucide) lucide.createIcons();
  }

  // Filter Jobs
  function applyFilters() {
    const { search, discipline, archetype, location, seniority, minSalary, minYoE, source, sortBy } = state.filters;
    const searchLower = search.trim().toLowerCase();

    state.filteredJobs = state.jobs.filter(job => {
      // 0. Role Archetype
      if (archetype && archetype !== 'all') {
        if ((job.archetype || '') !== archetype) return false;
      }

      // 1. Discipline Filter (General SWE vs ML / AI)
      if (discipline !== 'all') {
        if (discipline === 'Machine Learning / AI') {
          if (job.discipline !== 'Machine Learning / AI') return false;
        } else if (discipline === 'General Software') {
          if (job.discipline === 'Machine Learning / AI') return false;
        }
      }

      // 2. Search Query
      if (searchLower) {
        const titleMatch = job.title.toLowerCase().includes(searchLower);
        const compMatch = job.company.toLowerCase().includes(searchLower);
        const descMatch = (job.description || '').toLowerCase().includes(searchLower);
        const stackMatch = (job.tech_stack || []).some(t => t.toLowerCase().includes(searchLower));
        if (!titleMatch && !compMatch && !descMatch && !stackMatch) return false;
      }

      // 3. Location
      if (location !== 'all') {
        if (location === 'Remote') {
          if (job.work_model !== 'Remote' && job.city !== 'Remote') return false;
        } else if (job.city !== location) {
          return false;
        }
      }

      // 4. Granular Seniority: Senior Staff, Principal, Staff, Senior, Mid-Level, Software Engineer, Engineering Manager
      if (seniority !== 'all') {
        if (seniority === 'Senior Staff') {
          if (job.seniority !== 'Senior Staff') return false;
        } else if (seniority === 'Principal') {
          if (job.seniority !== 'Principal') return false;
        } else if (seniority === 'Staff') {
          if (job.seniority !== 'Staff') return false;
        } else if (seniority === 'Senior') {
          if (!['Senior', 'Lead'].includes(job.seniority)) return false;
        } else if (seniority === 'Mid-Level') {
          if (job.seniority !== 'Mid-Level') return false;
        } else if (seniority === 'Software Engineer') {
          if (job.seniority !== 'Software Engineer') return false;
        } else if (seniority === 'Engineering Manager') {
          if (job.seniority !== 'Engineering Manager') return false;
        }
      }

      // 5. Min Salary
      if (minSalary > 0 && job.salary) {
        if (job.salary.max < minSalary) return false;
      }

      // 6. Experience (YoE)
      if (minYoE !== 'all') {
        const reqYoE = parseInt(minYoE, 10);
        if (job.experience && job.experience.min_years < reqYoE) return false;
      }

      // 7. Source
      if (source !== 'all' && job.source !== source) return false;

      return true;
    });

    // Sort
    state.filteredJobs.sort((a, b) => {
      if (sortBy === 'salary-desc') {
        const salA = a.salary ? a.salary.max : 0;
        const salB = b.salary ? b.salary.max : 0;
        if (salB !== salA) return salB - salA;
        return (b.date_posted || '').localeCompare(a.date_posted || '');
      } else if (sortBy === 'date-desc') {
        return (b.date_posted || '').localeCompare(a.date_posted || '');
      } else if (sortBy === 'seniority-desc') {
        const score = (s) => (s === 'Principal' ? 5 : s === 'Senior Staff' ? 4 : s === 'Staff' ? 3 : s === 'Lead' ? 2 : 1);
        return score(b.seniority) - score(a.seniority);
      } else if (sortBy === 'company-asc') {
        return a.company.localeCompare(b.company);
      }
      return 0;
    });

    renderJobsList();
  }

  // Format exact date (YYYY-MM-DD -> MMM DD, YYYY)
  function formatExactDate(isoString) {
    if (!isoString) return 'Active Listing';
    const parts = isoString.split('-');
    if (parts.length === 3) {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const year = parts[0];
      const monthIdx = parseInt(parts[1], 10) - 1;
      const month = months[monthIdx] || parts[1];
      const day = parseInt(parts[2], 10);
      return `${month} ${day}, ${year}`;
    }
    return isoString;
  }

  // Render Job Cards
  function renderJobsList() {
    const list = state.filteredJobs;
    el.showingCount.textContent = list.length;

    if (state.filters.minSalary > 0) {
      el.salaryBadge.classList.remove('hidden');
      el.salaryBadge.textContent = `$${(state.filters.minSalary / 1000).toFixed(0)}k+ Target`;
    } else {
      el.salaryBadge.classList.add('hidden');
    }

    if (list.length === 0) {
      el.jobsContainer.innerHTML = '';
      el.emptyState.classList.remove('hidden');
      return;
    }

    el.emptyState.classList.add('hidden');

    const html = list.map(job => {
      const isSaved = state.savedJobIds.has(job.id);
      const initial = (job.company || 'C').charAt(0).toUpperCase();

      // Seniority Styling
      let seniorityBadgeClass = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700 font-semibold';
      if (job.seniority === 'Senior Staff') {
        seniorityBadgeClass = 'bg-amber-100 text-amber-900 dark:bg-amber-950/70 dark:text-amber-300 border-amber-300 dark:border-amber-800 font-bold';
      } else if (job.seniority === 'Principal') {
        seniorityBadgeClass = 'bg-purple-100 text-purple-900 dark:bg-purple-950/70 dark:text-purple-300 border-purple-300 dark:border-purple-800 font-bold';
      } else if (job.seniority === 'Staff') {
        seniorityBadgeClass = 'bg-indigo-100 text-indigo-900 dark:bg-indigo-950/70 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 font-bold';
      } else if (job.seniority === 'Senior' || job.seniority === 'Lead') {
        seniorityBadgeClass = 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-900 font-semibold';
      } else if (job.seniority === 'Mid-Level') {
        seniorityBadgeClass = 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800 font-semibold';
      } else if (job.seniority === 'Software Engineer') {
        seniorityBadgeClass = 'bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 border-teal-200 dark:border-teal-800 font-semibold';
      } else if (job.seniority === 'Engineering Manager') {
        seniorityBadgeClass = 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border-rose-200 dark:border-rose-800 font-semibold';
      }

      // Discipline Badge
      const isML = job.discipline === 'Machine Learning / AI';
      const disciplineBadge = isML ? `
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-950/80 dark:text-fuchsia-300 border border-fuchsia-200 dark:border-fuchsia-800">
          <i data-lucide="cpu" class="w-3 h-3"></i> ML / AI
        </span>
      ` : `
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
          General SWE
        </span>
      `;

      // Archetype Badge
      const archetypeBadge = job.archetype && job.archetype !== 'General Software' ? `
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-cyan-50 text-cyan-800 dark:bg-cyan-950/70 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800">
          ${job.archetype}
        </span>
      ` : '';

      // Salary badge
      let salaryHtml = '';
      if (job.salary) {
        salaryHtml = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <i data-lucide="badge-dollar-sign" class="w-3.5 h-3.5"></i>
            ${job.salary.display}
          </span>
        `;
      } else {
        salaryHtml = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
            Salary in description
          </span>
        `;
      }

      // Experience badge
      let yoeHtml = '';
      if (job.experience) {
        yoeHtml = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            <i data-lucide="hourglass" class="w-3.5 h-3.5"></i>
            ${job.experience.display}
          </span>
        `;
      }

      // Recruiter info
      const rec = job.recruiter || {};
      const recName = rec.recruiter_name || 'Technical Recruiter';
      const pocTitle = rec.point_of_contact || 'Talent Lead';
      const recProfileUrl = rec.profile_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(job.company + ' technical recruiter ' + job.city)}`;
      const hiringPostsUrl = rec.hiring_posts_url || `https://www.linkedin.com/search/results/content/?keywords=${encodeURIComponent(job.company + ' "hiring" ' + job.title)}`;

      // Tech tags
      const tags = (job.tech_stack || []).slice(0, 4);
      const tagsHtml = tags.map(t => `
        <span class="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
          ${t}
        </span>
      `).join('');

      const locIcon = job.work_model === 'Remote' ? 'globe' : 'map-pin';

      return `
        <div class="job-card group relative bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 hover:border-brand-500/80 dark:hover:border-brand-500 transition-all shadow-sm hover:shadow-md cursor-pointer" data-job-id="${job.id}">
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            
            <!-- Left: Company & Title -->
            <div class="flex items-start gap-3.5 flex-1 min-w-0">
              <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 border border-slate-200 dark:border-slate-700 flex items-center justify-center font-extrabold text-base text-slate-700 dark:text-slate-200 shadow-sm shrink-0">
                ${initial}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap mb-1">
                  <span class="font-bold text-sm text-slate-800 dark:text-slate-200">${job.company}</span>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border ${seniorityBadgeClass}">
                    ${job.seniority}
                  </span>
                  ${disciplineBadge}
                  ${archetypeBadge}
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400">
                    ${job.source}
                  </span>
                </div>
                
                <h3 class="text-base sm:text-lg font-bold text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors truncate">
                  ${job.title}
                </h3>

                <!-- Sub-meta: location & date -->
                <div class="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                  <span class="flex items-center gap-1 font-medium text-slate-600 dark:text-slate-300">
                    <i data-lucide="${locIcon}" class="w-3.5 h-3.5 text-slate-400"></i>
                    ${job.city} ${job.work_model !== 'On-site' ? '• ' + job.work_model : ''}
                  </span>
                  <span class="flex items-center gap-1 font-medium text-slate-600 dark:text-slate-300">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-400"></i>
                    ${formatExactDate(job.date_posted)}
                  </span>
                </div>

                <!-- Recruiter / Advertised By Bar -->
                <div class="mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center gap-2 text-xs flex-wrap" onclick="event.stopPropagation()">
                  <span class="text-[11px] text-slate-400 font-medium">Recruiter POC:</span>
                  <strong class="text-slate-700 dark:text-slate-300 font-semibold">${recName}</strong>
                  <span class="text-[11px] text-slate-400">(${pocTitle})</span>
                  
                  <!-- Direct Recruiter LinkedIn Profile Link -->
                  <a href="${recProfileUrl}" target="_blank" rel="noopener noreferrer" class="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-brand-50 hover:bg-brand-100 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300 border border-brand-200 dark:border-brand-900 transition-colors" title="View recruiter LinkedIn profile">
                    <i data-lucide="user" class="w-3 h-3 text-brand-600"></i>
                    <span>LinkedIn Profile</span>
                    <i data-lucide="external-link" class="w-2.5 h-2.5 text-brand-400"></i>
                  </a>

                  <!-- Direct Hiring Posts Link -->
                  <a href="${hiringPostsUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 hover:bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-900 transition-colors" title="Find people advertising this job on LinkedIn">
                    <i data-lucide="megaphone" class="w-3 h-3 text-amber-600"></i>
                    <span>Hiring Posts</span>
                    <i data-lucide="external-link" class="w-2.5 h-2.5 text-amber-400"></i>
                  </a>
                </div>

              </div>
            </div>

            <!-- Right: Salary & Quick Actions -->
            <div class="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-3 shrink-0">
              <div class="flex flex-wrap items-center gap-2">
                ${salaryHtml}
                ${yoeHtml}
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-2">
                <!-- Outreach button -->
                <button class="btn-outreach px-3 py-1.5 rounded-xl border border-brand-200 dark:border-brand-800 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-950/40 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm" data-job-id="${job.id}" title="Open outreach copilot">
                  <i data-lucide="send" class="w-3 h-3"></i>
                  <span>Message</span>
                </button>

                <!-- Direct Apply button -->
                <a href="${job.apply_url}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold flex items-center gap-1 shadow-sm transition-all" onclick="event.stopPropagation()">
                  <span>Apply</span>
                  <i data-lucide="external-link" class="w-3 h-3"></i>
                </a>

                <!-- Save Bookmark button -->
                <button class="btn-save p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-amber-500 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${isSaved ? 'text-amber-500 dark:text-amber-400' : ''}" data-job-id="${job.id}" title="${isSaved ? 'Remove from saved' : 'Save job'}" onclick="event.stopPropagation()">
                  <i data-lucide="bookmark" class="w-4 h-4 ${isSaved ? 'fill-amber-500' : ''}"></i>
                </button>
              </div>
            </div>

          </div>

          <!-- Bottom: Tech tags -->
          ${tags.length > 0 ? `
            <div class="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[11px] font-semibold text-slate-400 mr-1">Stack:</span>
                ${tagsHtml}
              </div>
              <span class="text-[11px] font-semibold text-brand-600 dark:text-brand-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                Full Details <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
              </span>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    el.jobsContainer.innerHTML = html;
    if (window.lucide) lucide.createIcons();

    // Attach card clicks
    document.querySelectorAll('.job-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('button') || e.target.closest('a')) return;
        const jobId = card.getAttribute('data-job-id');
        openJobDrawer(jobId);
      });
    });

    // Outreach buttons
    document.querySelectorAll('.btn-outreach').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const jobId = btn.getAttribute('data-job-id');
        openRecruiterModal(jobId);
      });
    });

    // Save buttons
    document.querySelectorAll('.btn-save').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const jobId = btn.getAttribute('data-job-id');
        toggleSaveJob(jobId);
      });
    });
  }

  // Render Companies Directory
  function renderCompanies() {
    const { location, search } = state.companyFilters;
    const searchLower = search.trim().toLowerCase();

    state.filteredCompanies = state.companies.filter(c => {
      if (location !== 'all' && c.metro !== location) return false;
      if (searchLower) {
        const nameMatch = c.name.toLowerCase().includes(searchLower);
        const indMatch = c.industry.toLowerCase().includes(searchLower);
        const stackMatch = (c.tech_stack || []).some(t => t.toLowerCase().includes(searchLower));
        if (!nameMatch && !indMatch && !stackMatch) return false;
      }
      return true;
    });

    if (state.filteredCompanies.length === 0) {
      el.companiesGrid.innerHTML = `
        <div class="col-span-full py-12 text-center text-slate-400">
          <p class="font-bold">No companies found matching criteria.</p>
        </div>
      `;
      return;
    }

    const html = state.filteredCompanies.map(c => {
      const initial = c.name.charAt(0).toUpperCase();
      const recruiterQuery = encodeURIComponent(`${c.name} technical recruiter ${c.metro.includes('York') ? 'New York' : 'Boston'}`);
      const recruiterUrl = `https://www.linkedin.com/search/results/people/?keywords=${recruiterQuery}`;

      const stackHtml = (c.tech_stack || []).map(t => `
        <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
          ${t}
        </span>
      `).join('');

      return `
        <div class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between gap-4">
          <div>
            <div class="flex items-start justify-between gap-3 mb-2">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-50 to-indigo-50 dark:from-slate-800 dark:to-slate-700 border border-slate-200 dark:border-slate-700 flex items-center justify-center font-bold text-slate-800 dark:text-slate-200">
                  ${initial}
                </div>
                <div>
                  <h3 class="font-bold text-base text-slate-900 dark:text-white leading-tight">${c.name}</h3>
                  <span class="text-xs text-brand-600 dark:text-brand-400 font-medium">${c.presence}</span>
                </div>
              </div>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-500">
                ${c.ats_board}
              </span>
            </div>

            <p class="text-xs text-slate-500 dark:text-slate-400 font-medium mb-3">
              ${c.industry}
            </p>

            <div class="flex flex-wrap gap-1 mb-2">
              ${stackHtml}
            </div>
          </div>

          <div class="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-2">
            <a href="${c.careers_url}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all">
              <i data-lucide="briefcase" class="w-3.5 h-3.5"></i>
              <span>Careers Page</span>
            </a>

            <a href="${recruiterUrl}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded-xl border border-brand-200 dark:border-brand-800 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-950/40 text-xs font-semibold flex items-center gap-1.5 transition-all">
              <i data-lucide="users" class="w-3.5 h-3.5"></i>
              <span>Find Recruiters</span>
            </a>
          </div>
        </div>
      `;
    }).join('');

    el.companiesGrid.innerHTML = html;
    if (window.lucide) lucide.createIcons();
  }

  // Toggle Save
  function toggleSaveJob(jobId) {
    if (state.savedJobIds.has(jobId)) {
      state.savedJobIds.delete(jobId);
    } else {
      state.savedJobIds.add(jobId);
    }
    localStorage.setItem('staffhunt_saved', JSON.stringify(Array.from(state.savedJobIds)));
    updateSavedBadge();
    renderJobsList();
  }

  // Open Drawer
  function openJobDrawer(jobId) {
    const job = state.jobs.find(j => j.id === jobId);
    if (!job) return;
    state.selectedJob = job;

    el.drawerCompany.textContent = job.company;
    el.drawerSource.textContent = job.source;
    const archLabel = job.archetype ? ` • ${job.archetype}` : '';
    el.drawerDiscipline.textContent = (job.discipline || 'General Software') + archLabel;
    el.drawerTitle.textContent = job.title;
    el.drawerLocation.innerHTML = `<i data-lucide="map-pin" class="w-3.5 h-3.5"></i> ${job.location || job.city}`;
    el.drawerDate.innerHTML = `<i data-lucide="calendar" class="w-3.5 h-3.5"></i> Posted: ${formatExactDate(job.date_posted)}`;

    el.drawerSalary.textContent = job.salary ? job.salary.display : 'Not explicitly stated in header';
    el.drawerExperience.textContent = job.experience ? job.experience.display : `${job.seniority} Tier Equivalent`;

    const rec = job.recruiter || {};
    el.drawerRecruiterPoc.textContent = `${rec.recruiter_name || 'Technical Recruiter'} - ${rec.point_of_contact || 'Talent Lead'} (${rec.recruiter_team || job.company + ' Talent'})`;

    const profileUrl = rec.profile_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(job.company + ' technical recruiter ' + job.city)}`;
    el.drawerBtnRecruiterProfile.href = profileUrl;

    const tech = job.tech_stack || [];
    if (tech.length > 0) {
      el.drawerTechStack.innerHTML = tech.map(t => `
        <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800">
          ${t}
        </span>
      `).join('');
    } else {
      el.drawerTechStack.innerHTML = `<span class="text-xs text-slate-400">See description details</span>`;
    }

    el.drawerDescription.textContent = job.description || job.snippet || 'No full description available.';
    el.drawerBtnApply.href = job.apply_url;

    const launchOutreach = () => openRecruiterModal(job.id);
    el.drawerBtnOutreach.onclick = launchOutreach;
    el.drawerBtnOutreachInline.onclick = launchOutreach;

    el.drawerBackdrop.classList.remove('hidden');
    el.drawer.classList.remove('translate-x-full');
    if (window.lucide) lucide.createIcons();
  }

  function closeJobDrawer() {
    el.drawerBackdrop.classList.add('hidden');
    el.drawer.classList.add('translate-x-full');
  }

  // Open Recruiter Modal
  function openRecruiterModal(jobId) {
    const job = state.jobs.find(j => j.id === jobId);
    if (!job) return;

    el.modalInitial.textContent = (job.company || 'C').charAt(0).toUpperCase();
    el.modalCompName.textContent = job.company;
    el.modalJobTitle.textContent = `${job.title} (${job.city})`;

    const rec = job.recruiter || {};
    el.modalPocName.textContent = rec.recruiter_name ? `${rec.recruiter_name} • ${rec.point_of_contact}` : (rec.point_of_contact || 'Technical Recruiter');
    el.modalTeamName.textContent = rec.recruiter_team || `${job.company} Talent Acquisition`;

    const profileUrl = rec.profile_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(job.company + ' technical recruiter ' + job.city)}`;
    el.modalBtnDirectProfile.href = profileUrl;

    const hiringPostsUrl = rec.hiring_posts_url || `https://www.linkedin.com/search/results/content/?keywords=${encodeURIComponent(job.company + ' "hiring" ' + job.title)}`;
    el.modalBtnHiringPosts.href = hiringPostsUrl;

    el.modalBtnRecruiter.href = rec.recruiter_search_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(job.company + ' technical recruiter ' + job.city)}`;
    el.modalBtnManager.href = rec.manager_search_url || `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(job.company + ' engineering manager ' + job.city)}`;

    let note = state.userProfile.outreach_template || '';
    const addressee = rec.recruiter_name ? rec.recruiter_name.split(' ')[0] : 'there';
    note = note.replace(/{{recruiter_name}}/g, addressee);
    note = note.replace(/{{company}}/g, job.company);
    note = note.replace(/{{job_title}}/g, job.title);
    note = note.replace(/{{location}}/g, job.city);
    note = note.replace(/{{user_name}}/g, state.userProfile.name || 'Varun Behl');

    el.modalOutreachText.value = note;
    el.copyToast.classList.add('opacity-0');

    el.recruiterModal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  }

  function closeRecruiterModal() {
    el.recruiterModal.classList.add('hidden');
  }

  async function copyOutreachMessage() {
    const text = el.modalOutreachText.value;
    try {
      await navigator.clipboard.writeText(text);
      el.copyToast.classList.remove('opacity-0');
      setTimeout(() => el.copyToast.classList.add('opacity-0'), 2500);
    } catch (err) {
      el.modalOutreachText.select();
      document.execCommand('copy');
      el.copyToast.classList.remove('opacity-0');
      setTimeout(() => el.copyToast.classList.add('opacity-0'), 2500);
    }
  }

  function openProfileModal() {
    el.prefUserName.value = state.userProfile.name || '';
    el.prefRoleTitle.value = (state.userProfile.target_roles || []).join(', ');
    el.prefOutreachTemplate.value = state.userProfile.outreach_template || '';
    el.profileModal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  }

  function saveProfile() {
    state.userProfile.name = el.prefUserName.value.trim();
    state.userProfile.target_roles = el.prefRoleTitle.value.split(',').map(s => s.trim());
    state.userProfile.outreach_template = el.prefOutreachTemplate.value;

    localStorage.setItem('staffhunt_profile', JSON.stringify(state.userProfile));
    el.profileModal.classList.add('hidden');
  }

  function openSavedModal() {
    const saved = state.jobs.filter(j => state.savedJobIds.has(j.id));
    if (saved.length === 0) {
      el.savedJobsList.innerHTML = `
        <div class="p-8 text-center text-slate-400">
          <p class="font-semibold">No saved jobs yet.</p>
          <p class="text-xs mt-1">Click the bookmark icon on any job card to track it here!</p>
        </div>
      `;
    } else {
      el.savedJobsList.innerHTML = saved.map(j => `
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <div>
            <h4 class="font-bold text-slate-900 dark:text-white">${j.title}</h4>
            <p class="text-xs text-slate-500">${j.company} • ${j.city} ${j.salary ? '• ' + j.salary.display : ''}</p>
          </div>
          <div class="flex items-center gap-2">
            <a href="${j.apply_url}" target="_blank" class="px-2.5 py-1 rounded-lg bg-brand-600 text-white font-semibold text-xs">Apply</a>
            <button class="p-1 text-red-500 hover:text-red-700" onclick="StaffHunt.removeSaved('${j.id}')">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>
        </div>
      `).join('');
    }
    el.savedModal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  }

  function bindEvents() {
    // Nav tabs
    el.navTabJobs.addEventListener('click', () => switchTab('jobs'));
    el.navTabCompanies.addEventListener('click', () => switchTab('companies'));
    if (el.mobileTabJobs) el.mobileTabJobs.addEventListener('click', () => switchTab('jobs'));
    if (el.mobileTabCompanies) el.mobileTabCompanies.addEventListener('click', () => switchTab('companies'));

    // Theme
    el.themeToggle.addEventListener('click', toggleTheme);

    // Discipline buttons (General SWE vs ML/AI)
    el.discButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        el.discButtons.forEach(b => {
          b.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
          b.classList.add('text-slate-600', 'dark:text-slate-400');
        });
        btn.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        btn.classList.remove('text-slate-600', 'dark:text-slate-400');

        state.filters.discipline = btn.getAttribute('data-disc');
        applyFilters();
      });
    });

    // Search
    el.searchInput.addEventListener('input', (e) => {
      state.filters.search = e.target.value;
      if (e.target.value) el.searchClear.classList.remove('hidden');
      else el.searchClear.classList.add('hidden');
      applyFilters();
    });

    el.searchClear.addEventListener('click', () => {
      el.searchInput.value = '';
      state.filters.search = '';
      el.searchClear.classList.add('hidden');
      applyFilters();
    });

    // Location pills
    el.locButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        el.locButtons.forEach(b => {
          b.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
          b.classList.add('text-slate-600', 'dark:text-slate-400');
        });
        btn.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        btn.classList.remove('text-slate-600', 'dark:text-slate-400');

        state.filters.location = btn.getAttribute('data-loc');
        applyFilters();
      });
    });

    // Company filter buttons
    el.compLocButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        el.compLocButtons.forEach(b => {
          b.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
          b.classList.add('text-slate-600', 'dark:text-slate-400');
        });
        btn.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        btn.classList.remove('text-slate-600', 'dark:text-slate-400');

        state.companyFilters.location = btn.getAttribute('data-comp-loc');
        renderCompanies();
      });
    });

    if (el.companySearchInput) {
      el.companySearchInput.addEventListener('input', (e) => {
        state.companyFilters.search = e.target.value;
        renderCompanies();
      });
    }

    // Select filters
    if (el.archetypeSelect) {
      el.archetypeSelect.addEventListener('change', (e) => {
        state.filters.archetype = e.target.value;
        applyFilters();
      });
    }

    el.senioritySelect.addEventListener('change', (e) => {
      state.filters.seniority = e.target.value;
      applyFilters();
    });

    el.salarySelect.addEventListener('change', (e) => {
      state.filters.minSalary = parseInt(e.target.value, 10);
      applyFilters();
    });

    el.yoeSelect.addEventListener('change', (e) => {
      state.filters.minYoE = e.target.value;
      applyFilters();
    });

    el.sourceSelect.addEventListener('change', (e) => {
      state.filters.source = e.target.value;
      applyFilters();
    });

    el.sortSelect.addEventListener('change', (e) => {
      state.filters.sortBy = e.target.value;
      applyFilters();
    });

    // Reset filters
    const resetFn = () => {
      el.searchInput.value = '';
      state.filters.search = '';
      state.filters.discipline = 'all';
      state.filters.archetype = 'all';
      state.filters.location = 'all';
      state.filters.seniority = 'all';
      state.filters.minSalary = 0;
      state.filters.minYoE = 'all';
      state.filters.source = 'all';
      state.filters.sortBy = 'salary-desc';

      if (el.archetypeSelect) el.archetypeSelect.value = 'all';
      el.salarySelect.value = '0';
      el.senioritySelect.value = 'all';
      el.yoeSelect.value = 'all';
      el.sourceSelect.value = 'all';
      el.sortSelect.value = 'salary-desc';

      el.discButtons.forEach(b => {
        if (b.getAttribute('data-disc') === 'all') {
          b.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        } else {
          b.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        }
      });

      el.locButtons.forEach(b => {
        if (b.getAttribute('data-loc') === 'all') {
          b.classList.add('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        } else {
          b.classList.remove('active', 'bg-white', 'dark:bg-slate-800', 'text-brand-600', 'dark:text-brand-300', 'shadow-sm');
        }
      });

      applyFilters();
    };

    el.resetBtn.addEventListener('click', resetFn);
    el.emptyResetBtn.addEventListener('click', resetFn);

    // Drawer close
    el.drawerClose.addEventListener('click', closeJobDrawer);
    el.drawerBackdrop.addEventListener('click', closeJobDrawer);

    // Recruiter Modal
    el.modalClose.addEventListener('click', closeRecruiterModal);
    el.modalBtnCopy.addEventListener('click', copyOutreachMessage);

    // Profile Modal
    el.btnOpenProfile.addEventListener('click', openProfileModal);
    el.profileModalClose.addEventListener('click', () => el.profileModal.classList.add('hidden'));
    el.prefSaveBtn.addEventListener('click', saveProfile);

    // Saved Jobs Modal
    el.btnSaved.addEventListener('click', openSavedModal);
    el.savedModalClose.addEventListener('click', () => el.savedModal.classList.add('hidden'));

    // ESC to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeJobDrawer();
        closeRecruiterModal();
        el.profileModal.classList.add('hidden');
        el.savedModal.classList.add('hidden');
      }
    });
  }

  // Global helper
  window.StaffHunt = {
    removeSaved: function (jobId) {
      state.savedJobIds.delete(jobId);
      localStorage.setItem('staffhunt_saved', JSON.stringify(Array.from(state.savedJobIds)));
      updateSavedBadge();
      openSavedModal();
      renderJobsList();
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
