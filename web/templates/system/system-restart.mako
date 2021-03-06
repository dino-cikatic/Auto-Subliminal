<%inherit file="/layout/page.mako"/>

<%!
    import autosubliminal
%>

<%block name="bodyContent">

    <!-- Modal -->
    <div class="modal fade" id="restartModal" tabindex="-1" data-keyboard="false" data-backdrop="static" role="dialog" aria-labelledby="restartModalLabel" aria-hidden="true">
        <div class="modal-dialog" role="document">
            <div class="modal-content text-center">
                <div class="modal-body">
                    <h2 class="modal-title" id="restartModalLabel">${message}</h2>
                    <br>
                    <i class="fa fa-refresh fa-5x fa-spin fa-fw" aria-hidden="true" title="Restarting..."></i>
                    <br>
                    <br>
                    <span>
                        If your page doesn't reload, click
                        <a href='${autosubliminal.WEBROOT}/home' class="btn btn-sm btn-default" role="button" aria-pressed="true">here</a>
                    </span>
                </div>
            </div>
        </div>
    </div>

</%block>

<%block name="footerContent">

    <script type="text/javascript" src="${autosubliminal.WEBROOT}/js/restart.js?v=${appUUID}"></script>

</%block>