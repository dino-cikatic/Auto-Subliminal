<%inherit file="/layout/page.mako"/>

<%!
    import autosubliminal
    from autosubliminal.utils import display_timestamp, get_disk_space_details, humanize_bytes
%>

<%block name="bodyContent">

    <div class="container">

        <div class="panel panel-default">

            <div class="panel-heading">
                <span class="h3 weighted">Status</span>
            </div>

            <div class="panel-body">

                <span class="row h4 weighted">Schedulers</span>

                <table id="scheduler" class="table table-condensed table-striped">

                    <thead>
                    <tr>
                        <th>Name</th>
                        <th>Last run</th>
                        <th>Next run</th>
                        <th>Running</th>
                    </tr>
                    </thead>

                    <tbody>
                        % for scheduler in list(autosubliminal.SCHEDULERS.values()):
                            <tr class="<% 'status-scheduler-running' if scheduler.running else '' %>">
                                <td class="main-column">${scheduler.name}</td>
                                <td>${display_timestamp(scheduler.last_run)}</td>
                                <td>${display_timestamp(scheduler.next_run)}</td>
                                <td>${scheduler.running}</td>
                            </tr>
                        %endfor
                    </tbody>

                </table>

                <span class="row h4 weighted">Disk space</span>

                <table id="diskspace" class="table table-condensed table-striped">

                    <thead>
                    <tr>
                        <th>Name</th>
                        <th>Location</th>
                        <th>Free space</th>
                    </tr>
                    </thead>

                    <tbody>
                    <tr>
                        <td class="main-column">Auto-Subliminal path</td>
                        <td>${autosubliminal.PATH}</td>
                        <%
                            free_bytes, total_bytes = get_disk_space_details(autosubliminal.PATH)
                            percentage = (float(free_bytes) / float(total_bytes) * 100)
                            percentage_string = '%.2f' % percentage + '%'
                        %>
                        <td>
                            ${humanize_bytes(free_bytes) + ' of ' + humanize_bytes(total_bytes) + ' (' + percentage_string + ')'}
                            % if percentage < 10:
                                <i class="fa fa-exclamation-triangle text-danger" aria-hidden="true" title="Low disk space"></i>
                            % endif
                        </td>
                    </tr>
                        % for index, path in enumerate(autosubliminal.VIDEOPATHS):
                            <tr>
                                <%
                                    path_suffix = ''
                                    if len(autosubliminal.VIDEOPATHS) > 1:
                                        path_suffix = index + 1
                                %>
                                <td class="main-column">Video path ${path_suffix}</td>
                                <td>${path}</td>
                                <%
                                    free_bytes, total_bytes = get_disk_space_details(path)
                                    percentage = (float(free_bytes) / float(total_bytes) * 100)
                                    percentage_string = '%.2f' % percentage + '%'
                                %>
                                <td>
                                    ${humanize_bytes(free_bytes) + ' of ' + humanize_bytes(total_bytes) + ' (' + percentage_string + ')'}
                                    % if percentage < 10:
                                        <i class="fa fa-exclamation-triangle text-danger" aria-hidden="true" title="Low disk space"></i>
                                    % endif
                                </td>
                            </tr>
                        %endfor
                    </tbody>

                </table>

            </div>

        </div>

    </div>

</%block>

<%block name="footerContent">

    <script type="text/javascript" src="${autosubliminal.WEBROOT}/js/status.js?v=${appUUID}"></script>

</%block>
