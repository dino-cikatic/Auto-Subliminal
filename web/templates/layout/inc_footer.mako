<%!
    import autosubliminal
    from autosubliminal import version
    from autosubliminal.utils import get_next_scheduler_run_in_ms
%>

<!-- Footer -->
<div class="navbar navbar-fixed-bottom panel-footer text-center navbar-footer-small">
    <input type="hidden" id="scandisk-nextrun-time-ms" value="${get_next_scheduler_run_in_ms(autosubliminal.SCANDISK)}">
    <input type="hidden" id="checksub-nextrun-time-ms" value="${get_next_scheduler_run_in_ms(autosubliminal.CHECKSUB)}">
    <span>Auto-Subliminal version : ${version.RELEASE_VERSION}</span>
    <span class="separator">|</span>
    <span>
        Next disk scan in :
        <span id="scandisk-nextrun"></span>
    </span>
    <span class="separator">|</span>
    <span>
        Next subtitle check in :
        <span id="checksub-nextrun"></span>
    </span>
</div>

<!-- Vendor javascript -->
<% vendor_js = autosubliminal.DEVELOPER and "vendor.js" or "vendor.min.js" %>
<script type="text/javascript" src="${autosubliminal.WEBROOT}/js/${vendor_js}"></script>

<!-- Auto-Subliminal javascript (applies to all pages) -->
<script type="text/javascript" src="${autosubliminal.WEBROOT}/js/autosubliminal.js"></script>