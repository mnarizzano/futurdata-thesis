def render_sidebar() -> str:
    return '''
<aside class="sidebar">
  <div class="brand"><div class="brand-mark">◆</div><div><h1 id="productNameSide">Disassembly Wizard</h1><p id="productSubtitle"></p></div></div>
  <div class="side-title">STEPS</div>
  <div id="stepsList"></div>
  <button class="overview-btn" onclick="showOverview()">Overview</button>
</aside>'''


def render_main_content() -> str:
    return '''
<main class="content">
  <section id="welcomeView" class="welcome-view">
    <div class="welcome-card">
      <div class="welcome-copy">
        <div class="step-kicker">INTERACTIVE DISASSEMBLY GUIDE</div>
        <h2 id="welcomeTitle">Disassembly Wizard</h2>
        <p>Follow the guided instructions to safely disassemble the product step by step, grade each recovered component, and generate a final recovery report.</p>
        <div class="welcome-stats">
          <div><span>Steps</span><strong id="welcomeSteps">0</strong></div>
          <div><span>Components</span><strong id="welcomeComponents">0</strong></div>
          <div><span>Product weight</span><strong id="welcomeWeight">—</strong></div>
        </div>
      </div>
      <div class="welcome-visual" id="welcomeImage"></div>
      <button class="primary welcome-start" onclick="startWizard()">Start disassembly →</button>
    </div>
  </section>

  <section id="stepView" class="hidden">
    <div class="progress"><div id="progressBar"></div></div>
    <div class="step-kicker" id="stepCounter"></div>
    <h2 id="stepOperation"></h2>
    <div id="toolsBox"></div>

    <section class="step-layout">
      <div class="image-panel"><div id="imageBox"></div></div>
      <div class="instructions-panel">
        <h3>Instructions</h3>
        <div id="actionsList"></div>
        <div id="continuesAs"></div>
      </div>
    </section>

    <section class="parts-section">
      <h3>Parts removed in this step — grade each one</h3>
      <div id="outputsList" class="parts-grid"></div>
    </section>

    <div class="nav-row">
      <button id="prevBtn" class="secondary" onclick="previousStep()">← Back</button>
      <button class="secondary" onclick="showOverview()">Overview</button>
      <button id="nextBtn" class="primary" onclick="nextStep()">Next →</button>
    </div>
  </section>

  <section id="summaryView" class="summary-view hidden">
    <div class="summary-hero">
      <div class="complete-icon">✓</div>
      <div>
        <div class="step-kicker">DISASSEMBLY REPORT</div>
        <h2>Disassembly completed</h2>
        <p id="summarySubtitle"></p>
      </div>
    </div>

    <div id="summaryWarning"></div>
    <div id="summaryStats" class="summary-stats"></div>

    <div class="summary-table-wrap">
      <table class="summary-table">
        <thead><tr><th>Image</th><th>Component</th><th>Material</th><th>Nominal</th><th>Measured</th><th>Grading</th><th>Destination</th></tr></thead>
        <tbody id="summaryRows"></tbody>
      </table>
    </div>

    <div class="summary-actions">
      <button class="secondary" onclick="backToSteps()">← Back to steps</button>
      <button class="secondary" onclick="window.print()">Print / Save PDF</button>
      <button class="primary restart-btn" onclick="restartWizard()">Restart</button>
    </div>
  </section>

  <section id="overviewPanel" class="overview-panel hidden">
    <button class="close-overview" onclick="hideOverview()">×</button>
    <h2>Product Overview</h2>
    <div id="overviewContent"></div>
  </section>

  <div id="imageModal" class="image-modal" onclick="closeImage()"><img id="modalImage" alt="Expanded image"></div>
</main>'''
