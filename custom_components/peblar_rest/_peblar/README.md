# Vendored `python-peblar`

Copy of [`peblar==2.1.0`](https://github.com/frenck/python-peblar/releases/tag/v2.1.0)
(MIT, see `LICENSE.md`), excluding the CLI. The only change is making one
`TYPE_CHECKING` import in `peblar.py` relative.

It is vendored because Home Assistant bundles an older `peblar` release for its
built-in Peblar integration. Requiring a different version of the shared `peblar`
package makes Home Assistant replace it at runtime, which breaks imports such as
`No module named 'peblar.utils'`.
