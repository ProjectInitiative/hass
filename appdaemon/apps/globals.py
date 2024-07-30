import appdaemon.plugins.hass.hassapi as hass

class GlobalNotify(hass.Hass):
    def initialize(self):
        self.notification_groups = self.args.get("groups", {})
        # build "all" group
        self.notification_groups["all"] = []
        self.log(self.notification_groups)

        for group, devices in self.notification_groups.items():
            # prevent infinite loop
            if group == "all":
                continue
            for device in devices:
                self.log(f"Group: {device}")
                self.notification_groups["all"].append(device)

        self.log("Global Notification Library initialized with groups: " + ", ".join(self.notification_groups.keys()))

    def notify(self, group, message, **kwargs):
        kwargs["message"] = message
        if group in self.notification_groups:
            for device in self.notification_groups[group]:
                self.call_service(f"notify/{device}", **kwargs)
            self.log(f"Sent notification to group: {group}")
        else:
            self.log(f"Notification group '{group}' not found")
