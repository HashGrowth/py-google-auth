# py-google-auth

## Introduction
Headless implementation of Google web login (with support for 2-Step Verification) in Python

`py-google-auth` exposes a high-level REST API that can be used for headless login at [Google Accounts: Sign in](https://accounts.google.com/ServiceLogin). 

**Note**: This project is in "alpha" version right now. We are actively developing it and expect it to be beta-ready in next couple of weeks.

## License
MIT.
The license text is available in `LICENSE` file in root of this repo.

## Supported 2-step verification 'steps'
We support following 'steps' (i.e. methods) offered by Google in [2-step verification](https://myaccount.google.com/security/signinoptions/two-step-verification):
* **Voice or text message**: Verification codes are sent by text message.
* **Backup codes**: 10 single-use codes are active at this time, but you can generate more as needed.
* **Google prompt**: Get a Google prompt on your phone and just tap Yes to sign in.
* **Authenticator app**: Use the Authenticator app to get free verification codes, even when your phone is offline. Available for Android and iPhone.
* **Backup phone**: Add a backup phone so you can still sign in if you lose your phone.

## Unsupported 2-step verification 'step'
We **DONT* support following 'step' (i.e. method):
* **Security Key**: A Security Key is a small physical device used for signing in. It plugs into your computer's USB port.

## Documentation
We are in process of writing documentation, which will be hosted at [http://py-google-auth.readthedocs.io/en/latest/](http://py-google-auth.readthedocs.io/en/latest/). In the meantime, you can read early draft of documentation [on this page](https://github.com/HashGrowth/py-google-auth/tree/packaging#py-google-auth).

## FAQs
To be done.

## Maintainers/Contact

1. [Swati Jaiswal](https://github.com/curioswati) (Current maintainer)

If Swati isn't responding, feel free to poke [Amber Jain](https://github.com/amberj) or [Pulkit Vaishnav](https://github.com/pulkitvaishnav/).

## How to Contribute

1. Check for [open issues or open a fresh issue](https://github.com/HashGrowth/py-google-auth/issues) to start a discussion around a feature idea or a bug.
2. Fork the repository on GitHub to start making your changes to the master branch (or branch off of it).
3. Write a test which shows that the bug was fixed or that the feature works as expected.
4. Send a pull request and poke the maintainer until it gets merged and published :)