---
- name: "Load allianz.server.conf"
  read_allianz_server_conf:
  register: server_conf

- name: Create a new host or update an existing host's info
  local_action:
    module: zabbix_tag
    server_url: "{{ zabbix_server }}"
    login_user: tu_ansible
    login_password: pwd4ansible
    host_name: "{{inventory_hostname |replace ('.srv.allianz', '')}}"
    stage: "{{server_conf.content.STAGE}}"
    mandant: "{{server_conf.content.MANDANT}}"
    servertype: "{{server_conf.content.SERVERTYPE}}"
    jbossprofiles: "{{server_conf.content.JBOSSPROFILES | default('')}}"
    tomcatprofiles: "{{server_conf.content.TOMCATPROFILES| default('')}}"
    asifportoffsets: "{{server_conf.content.ASIF_PORTOFFSETS| default('')}}"

#- name: Update zabbix configuration
#  cron:
#    name: "update zabbix configuration"
#    minute: "*/15"
#    job: "cd /etc/zabbix; if ! git diff --quiet remotes/origin/HEAD; then git pull; service zabbix-agent restart; fi"

- name: "Update git repo"
  shell: cd /etc/zabbix && git fetch origin && git reset --hard origin/master && git checkout master && git pull
  environment:
    http_proxy: http://fr003-e2-svr.zone2.proxy.allianz:8090
    https_proxy: http://fr003-e2-svr.zone2.proxy.allianz:8090
  become: true

- name: "Re-create zabbix_agentd.conf"
  become: true
  template: 
    src: ../../zabbix/templates/zabbix_agentd.conf.j2 
    dest: /etc/zabbix/zabbix_agentd.conf
    mode: 644

- stat:
    path: /usr/lib/systemd/system/zabbix-agent.service
  register: service_file

- name: install customized zabbix-agent systemd unit file
  template:
    src: ../../zabbix/templates/zabbix-agent-systemd.service
    dest: /usr/lib/systemd/system/zabbix-agent.service
    mode: 644
  when: service_file.stat.exists

- name: start zabbix-agent
  systemd:
    state: started
    name: zabbix-agent 
    daemon_reload: yes
  when: service_file.stat.exists

- name: restart zabbix-agent
  service:
    name: zabbix-agent
    state: restarted
    enabled: true
  become: true
