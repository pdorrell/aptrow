(load-this-project
 `( (:search-extensions (".py"))
    (:python-executable ,*python-3-executable*)
    (:main-file ,(concat (project-base-directory) "aptrow_server.py"))
    (:run-project-command (python-run-main-file) ) ) )
