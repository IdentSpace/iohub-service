# Devices API v2

Base path: `/api/v2`. Existing routes under `/api/device` remain available.
No database migration is required.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/devices` | List configured devices including capabilities; no hardware access |
| GET | `/devices/{id}` | Device identity and capabilities; no hardware access |
| GET | `/devices/{id}/capabilities` | Supported commands, enum argument options and state fields |
| GET | `/devices/{id}/state` | Read current state through the shared runtime manager |
| GET | `/devices/{id}/snapshot` | Camera JPEG image; caching disabled |
| GET | `/devices/{id}/stream` | Camera MJPEG stream; caching disabled |

Camera routes return 404 for missing devices, 409 for non-camera devices,
502 for camera failures, and 504 for timeouts. The first stream frame is read
before sending response headers. Later failures terminate the stream because
the HTTP status can no longer change. Each client opens its own camera stream;
disconnecting closes its iterator without closing the shared driver.
These routes inherit the existing API's authentication behavior (currently
no authentication enforcement). Camera credentials remain server-side driver
arguments; database-backed credential configuration is not implemented.
| POST | `/devices/{id}/commands` | Validate and execute a command |

Example request body:

```json
{"cmd": "switch", "arg": "on"}
```

A barrier accepts `{"cmd": "open"}` or `{"cmd": "close"}` without an argument.
Readers currently advertise no executable commands. Clients must use the command
list for the individual device rather than the global command enum.

Responses are typed resources, without the legacy IHCApiResponse wrapper.
The list response uses `items`. State responses separate `connection` from
`values`. `observed_at` is the UTC time the state was read, not the time of the
last physical change. State fields are defined by each driver's capabilities.
Discovery deliberately includes no live state, so listing devices cannot block
on hardware. Unknown driver configurations remain visible in the list with
`configuration_error`; operational requests return 409.

Errors use HTTP status codes: 404 for missing devices, 409 for invalid driver
configuration, 422 for invalid input or unsupported commands, and 502 for
hardware failures. Application error details contain `code` and `message`;
FastAPI's request validation errors use its standard detail array.
Commands run synchronously and return a CommandResponse. No event stream,
CRUD endpoints or new authentication scheme are introduced in this version.

Driver authors must implement the abstract class method
`get_capabilities() -> DeviceCapabilities`. It must not open hardware connections.
Dummy drivers inherit metadata from their scanner/reader base classes.
The same descriptors validate v2 commands before the runtime manager dispatches
them. Existing direct driver calls and legacy routes retain their previous
validation behavior.

The models and endpoints appear in the application's OpenAPI documentation.


All capability `label` fields contain stable translation slugs, never localized
text. Namespaces are `command.*`, `argument.*`, and `state.*`, for example
`command.open`, `argument.on`, and `state.moving`. Clients own translations and
can use the slug as a fallback when a translation is missing. Slugs are validated
by the descriptor models. User-configured device names remain unchanged.
Hardware discovery on the IOHub server:

- `GET /api/v2/hardware/serial`: COM/TTY ports and USB serial adapters with
  `host`, description, manufacturer, serial number and USB VID/PID.
- `GET /api/v2/hardware/cameras?max_index=4`: probe indices 0 through 4 on
  Windows/macOS, or `/dev/video*` paths on Linux. Each probe has a three-second
  process timeout. `items[].host` can be used as the `local_camera` host.
  `available=false` indicates missing OpenCV support; `issues` reports failed
  probes. Busy cameras can fail probing. The index limit accepts 0 through 15.

These endpoints enumerate attached serial/video devices, not arbitrary USB
hardware or devices on the browser's machine. Camera probing briefly opens the
hardware; serial discovery does not open ports.

